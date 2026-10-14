"""Guest-facing web app served on the local network. Selfies are processed in memory and never saved."""
import io
import os
import secrets
import socket
import threading
import time
import zipfile
from pathlib import Path

import qrcode
from fastapi import FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import HTMLResponse, RedirectResponse, Response, StreamingResponse
from PIL import Image, ImageDraw, ImageFont

from .faces import FaceEngine
from .index import EventIndex, build_index, purge

SESSION_TTL = 30 * 60  # guest results live 30 min, in memory only
PORT = int(os.environ.get("LOCALLENS_PORT", 8000))
PAGES = Path(__file__).resolve().parent / "pages"
WATERMARK = "PREVIEW"

app = FastAPI()
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
def start_setup(request: Request, folder: str = Form(...), event_name: str = Form(...), hours: float = Form(72)):
    require_laptop(request)
    if job["state"] == "running":
        raise HTTPException(409, "Already indexing.")

    def run():
        global index
        job.update(state="running", done=0, total=0, error="")
        try:
            build_index(folder, hours, event_name,
                        progress=lambda d, t: job.update(done=d, total=t))
            sessions.clear()
            index = EventIndex()
            job["state"] = "ready"
        except Exception as e:  # surface any failure to the setup screen
            job.update(state="error", error=str(e))

    threading.Thread(target=run, daemon=True).start()
    return {"ok": True}


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
    draw = ImageDraw.Draw(img, "RGBA")
    font = ImageFont.load_default(size=max(24, img.width // 10))
    w, h = img.size
    for y in range(0, h, h // 3 or 1):
        draw.text((w // 10, y + h // 8), WATERMARK, fill=(255, 255, 255, 110), font=font)
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
