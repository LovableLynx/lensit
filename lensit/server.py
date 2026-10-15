"""Guest-facing web app served on the local network. Selfies are processed in memory and never saved."""
import io
import os
import secrets
import socket
import subprocess
import sys
import threading
import time
import zipfile
from pathlib import Path

import qrcode
from fastapi import FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import HTMLResponse, RedirectResponse, Response, StreamingResponse
from fastapi.staticfiles import StaticFiles
from PIL import Image, ImageDraw, ImageFont

from .faces import FaceEngine
from .index import EXTS, EventIndex, build_index, purge

SESSION_TTL = 30 * 60  # guest results live 30 min, in memory only
PORT = int(os.environ.get("LENSIT_PORT", 8000))
PAGES = Path(__file__).resolve().parent / "pages"
STATIC = Path(__file__).resolve().parent / "static"
WATERMARK = "PREVIEW"

app = FastAPI()
app.mount("/static", StaticFiles(directory=STATIC), name="static")
engine = FaceEngine()
index: EventIndex | None = EventIndex() if EventIndex.exists() else None
sessions: dict[str, tuple[float, list[int]]] = {}  # token -> (created, photo ids)
job = {"state": "idle", "done": 0, "total": 0, "error": ""}


def lan_ip() -> str:
    try:  # UDP connect sends no packets; just picks the LAN interface
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("10.255.255.255", 1))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except OSError:
        return "127.0.0.1"


def guest_url() -> str:
    return f"http://{lan_ip()}:{PORT}/"


def janitor():
    global index
    while True:
        now = time.time()
        for t in [t for t, (c, _) in sessions.items() if now - c > SESSION_TTL]:
            sessions.pop(t, None)
        if index and index.expired():
            print("Event expired: deleting face index.")
            sessions.clear()
            index = None
            purge()
        time.sleep(30)


threading.Thread(target=janitor, daemon=True).start()


def require_laptop(request: Request):
    """Setup screens are only reachable from the photographer's own laptop, never from guests' phones."""
    if request.client.host not in ("127.0.0.1", "::1", "localhost"):
        raise HTTPException(403, "Setup is only available on the photographer's laptop.")


def page(name: str, **values) -> str:
    html = (PAGES / name).read_text(encoding="utf-8")
    for k, v in values.items():
        html = html.replace("{{" + k + "}}", str(v))
    return html


def session(token: str) -> list[int]:
    s = sessions.get(token)
    if not s:
        raise HTTPException(404, "Session expired - take a new selfie.")
    return s[1]


# ---------- Photographer onboarding (laptop only) ----------

@app.get("/setup", response_class=HTMLResponse)
def setup_page(request: Request):
    require_laptop(request)
    return page("setup.html", guest_url=guest_url())


@app.post("/setup")
def start_setup(request: Request, folder: str = Form(...), event_name: str = Form(...), hours: float = Form(72),
                agree: str = Form("")):
    require_laptop(request)
    if not agree:
        raise HTTPException(400, "Please confirm the photographer responsibilities first.")
    if job["state"] == "running":
        raise HTTPException(409, "Already indexing.")

    def run():
        global index
        job.update(state="running", done=0, total=0, error="")
        try:
            build_index(folder.strip().strip('"'), hours, event_name.strip(),
                        progress=lambda d, t: job.update(done=d, total=t))
            sessions.clear()
            index = EventIndex()
            job["state"] = "ready"
        except Exception as e:  # surface any failure to the setup screen
            job.update(state="error", error=str(e))

    threading.Thread(target=run, daemon=True).start()
    return {"ok": True}


# Native folder picker (Windows). Runs on the laptop itself, so it's only reachable from the laptop.
FOLDER_DIALOG = (
    "Add-Type -AssemblyName System.Windows.Forms;"
    "$o = New-Object System.Windows.Forms.Form -Property @{TopMost=$true};"
    "$f = New-Object System.Windows.Forms.FolderBrowserDialog;"
    "$f.Description = 'Choose the folder with your event photos';"
    "if ($f.ShowDialog($o) -eq 'OK') { [Console]::Out.Write($f.SelectedPath) }"
)


@app.post("/setup/browse")
def browse_folder(request: Request):
    require_laptop(request)
    if sys.platform != "win32":
        return {"error": "Folder picker is only available on Windows. Paste the folder path instead."}
    out = subprocess.run(["powershell", "-NoProfile", "-STA", "-Command", FOLDER_DIALOG],
                         capture_output=True, text=True, creationflags=subprocess.CREATE_NO_WINDOW)
    return {"path": out.stdout.strip()}


@app.get("/setup/folder")
def check_folder(request: Request, path: str):
    require_laptop(request)
    folder = Path(path.strip().strip('"'))
    if not folder.is_dir():
        return {"ok": False, "error": "That folder doesn't exist. Check the path or use Browse."}
    count = sum(1 for f in folder.rglob("*") if f.suffix.lower() in EXTS)
    if not count:
        return {"ok": False, "error": "No photos (JPG, PNG or WebP) found in that folder."}
    return {"ok": True, "count": count}


@app.get("/setup/status")
def setup_status(request: Request):
    require_laptop(request)
    info = dict(job)
    if index:
        info.update(event=index.meta.get("event_name", ""), photos=len(index.photos),
                    faces=len(index.vecs), expires_at=index.meta["expires_at"])
    return info


@app.post("/setup/purge")
def setup_purge(request: Request):
    global index
    require_laptop(request)
    sessions.clear()
    index = None
    purge()
    job["state"] = "idle"
    return {"ok": True}


# ---------- Guest flow ----------

@app.get("/", response_class=HTMLResponse)
def home(request: Request):
    if request.client.host in ("127.0.0.1", "::1") and not index:
        return RedirectResponse("/setup")
    name = index.meta.get("event_name", "this event") if index else ""
    return page("guest.html", event_name=name, ready="true" if index else "false")


@app.post("/search")
async def search(selfie: UploadFile = File(...), consent: str = Form("")):
    if consent != "yes":
        raise HTTPException(400, "Please agree to the consent note first.")
    if not index:
        raise HTTPException(503, "The photographer hasn't loaded this event yet.")
    data = await selfie.read()
    try:
        faces = engine.embeddings_from_bytes(data)
    except ValueError:
        raise HTTPException(400, "That file isn't an image.")
    finally:
        del data
    if len(faces) == 0:
        raise HTTPException(400, "No face found - try again in better light.")
    # Use the first detected face; the embedding is discarded after matching.
    matches = index.match(faces[0])
    token = secrets.token_urlsafe(16)
    sessions[token] = (time.time(), matches)
    return {"token": token, "count": len(matches)}


@app.get("/preview/{token}/{i}")
def preview(token: str, i: int):
    ids = session(token)
    if not 0 <= i < len(ids):
        raise HTTPException(404)
    img = Image.open(index.path(ids[i])).convert("RGB")
    img.thumbnail((800, 800))
    # Diagonal tiled watermark, so it survives any square crop in the guest's grid.
    w, h = img.size
    size = max(18, min(w, h) // 9)
    font = ImageFont.load_default(size=size)
    tile = Image.new("RGBA", (w * 2, h * 2), (0, 0, 0, 0))
    draw = ImageDraw.Draw(tile)
    step_x, step_y = size * 7, size * 3
    for row, y in enumerate(range(0, h * 2, step_y)):
        for x in range(-(row % 2) * step_x // 2, w * 2, step_x):
            draw.text((x, y), WATERMARK, fill=(255, 255, 255, 95), font=font)
    tile = tile.rotate(30, resample=Image.BICUBIC)
    left, top = (tile.width - w) // 2, (tile.height - h) // 2
    img.paste(tile.crop((left, top, left + w, top + h)), (0, 0), tile.crop((left, top, left + w, top + h)))
    buf = io.BytesIO()
    img.save(buf, "JPEG", quality=70)
    return Response(buf.getvalue(), media_type="image/jpeg")


@app.get("/download/{token}")
def download(token: str):
    ids = session(token)
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_STORED) as z:
        for pid in ids:
            p = index.path(pid)
            z.write(p, p.name)
    buf.seek(0)
    return StreamingResponse(buf, media_type="application/zip",
                             headers={"Content-Disposition": "attachment; filename=my-event-photos.zip"})


@app.get("/qr.png")
def qr_png():
    buf = io.BytesIO()
    qrcode.make(guest_url()).save(buf, "PNG")
    return Response(buf.getvalue(), media_type="image/png")
