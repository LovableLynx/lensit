"""Build and query the local face index for one event."""
import json
import os
import shutil
import sys
import time
from pathlib import Path

import cv2
import numpy as np

from .faces import FaceEngine, MATCH_THRESHOLD

if getattr(sys, "frozen", False):  # packaged .exe: keep face data in the user's app-data folder
    DATA_DIR = Path(os.environ.get("LOCALAPPDATA", Path.home())) / "LensIt" / "data"
else:
    DATA_DIR = Path(__file__).resolve().parent.parent / "data"
EXTS = {".jpg", ".jpeg", ".png", ".webp"}


def build_index(photo_dir: str, expire_hours: float, event_name: str = "My event", progress=None):
    photo_dir = Path(photo_dir).resolve()
    if not photo_dir.is_dir():
        raise ValueError("Folder not found")
    photos = sorted(p for p in photo_dir.rglob("*") if p.suffix.lower() in EXTS)
    if not photos:
        raise ValueError("No photos found in that folder")
    engine = FaceEngine()
    vecs, owners = [], []
    start = time.time()
    for i, p in enumerate(photos):
        img = cv2.imread(str(p))
        if img is None:
            continue
        e = engine.embeddings(img)
        vecs.append(e)
        owners += [i] * len(e)
        print(f"[{i + 1}/{len(photos)}] {p.name}: {len(e)} face(s)")
        if progress:
            progress(i + 1, len(photos))
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    np.savez(DATA_DIR / "index.npz",
             vecs=np.concatenate(vecs) if vecs else np.zeros((0, 128), np.float32),
             owners=np.array(owners, np.int32))
    meta = {"event_name": event_name, "photo_dir": str(photo_dir), "photos": [str(p.relative_to(photo_dir)) for p in photos],
            "expires_at": time.time() + expire_hours * 3600}
    (DATA_DIR / "meta.json").write_text(json.dumps(meta))
    print(f"Indexed {len(photos)} photos, {len(owners)} faces in {time.time() - start:.0f}s")


def purge():
    """Delete all face embeddings and event metadata (photos themselves are untouched)."""
    if DATA_DIR.exists():
        shutil.rmtree(DATA_DIR)
    print("Face index deleted.")


class EventIndex:
    @staticmethod
    def exists():
        return (DATA_DIR / "meta.json").exists()

    def __init__(self):
        z = np.load(DATA_DIR / "index.npz")
        self.vecs, self.owners = z["vecs"], z["owners"]
        self.meta = json.loads((DATA_DIR / "meta.json").read_text())
        self.photo_dir = Path(self.meta["photo_dir"])
        self.photos = self.meta["photos"]

    def expired(self):
        return time.time() > self.meta["expires_at"]

    def match(self, selfie_vec: np.ndarray) -> list[int]:
        return [pid for pid, _ in self.match_scored(selfie_vec)]

    def match_scored(self, selfie_vec: np.ndarray) -> list[tuple[int, float]]:
        """(photo id, best face score) for every photo at or above the match threshold, best first."""
        if len(self.vecs) == 0:
            return []
        sims = self.vecs @ selfie_vec
        best = {}
        for idx in np.nonzero(sims >= MATCH_THRESHOLD)[0]:
            pid = int(self.owners[idx])
            best[pid] = max(best.get(pid, 0), float(sims[idx]))
        return sorted(best.items(), key=lambda kv: kv[1], reverse=True)

    def path(self, pid: int) -> Path:
        return self.photo_dir / self.photos[pid]
