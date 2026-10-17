"""Face detection (YuNet) and recognition (SFace) via OpenCV. Both models are Apache-2.0 (opencv_zoo)."""
import hashlib
import sys
import urllib.request
from pathlib import Path

import cv2
import numpy as np

if getattr(sys, "frozen", False):  # packaged .exe: models are bundled inside it
    MODELS_DIR = Path(sys._MEIPASS) / "models"
else:
    MODELS_DIR = Path(__file__).resolve().parent.parent / "models"
# Pinned to exact upstream commits and verified by SHA-256, so a tampered download is refused.
MODELS = {
    "yunet.onnx": (
        "https://github.com/opencv/opencv_zoo/raw/f12e12798e8314f7c074a6656816c048dcc95b7a/models/face_detection_yunet/face_detection_yunet_2023mar.onnx",
        "8f2383e4dd3cfbb4553ea8718107fc0423210dc964f9f4280604804ed2552fa4",
    ),
    "sface.onnx": (
        "https://github.com/opencv/opencv_zoo/raw/ba91a3b91d00d76e86540d4013f944bd6b514e39/models/face_recognition_sface/face_recognition_sface_2021dec.onnx",
        "0ba9fbfa01b5270c96627c4ef784da859931e02f04419c829e83484087c34e79",
    ),
}
# Cosine-similarity threshold recommended by OpenCV for SFace.
MATCH_THRESHOLD = 0.363
# In real-photo tests, wrong matches scored 38-41%; real ones with a good selfie scored 44-66%.
# Between the two thresholds a photo is shown as "Maybe you?" rather than a sure match.
STRONG_THRESHOLD = 0.45
# A selfie whose face is this blurry (or small) loses the detail matching needs, so we ask for a retake.
MIN_SHARPNESS = 100
MIN_FACE_PX = 80
MAX_SIDE = 1280  # downscale big camera photos; keeps an 8 GB laptop happy


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def download_models():
    """Download missing models and verify every model file's checksum before it is used."""
    MODELS_DIR.mkdir(exist_ok=True)
    for name, (url, sha) in MODELS.items():
        dest = MODELS_DIR / name
        if not dest.exists():
            print(f"Downloading {name} ...")
            tmp = dest.with_suffix(".part")
            urllib.request.urlretrieve(url, tmp)
            if _sha256(tmp) != sha:
                tmp.unlink()
                raise RuntimeError(f"{name} failed its checksum - download refused.")
            tmp.rename(dest)
        elif _sha256(dest) != sha:
            raise RuntimeError(f"{name} has been modified - delete the models folder and run setup again.")


class FaceEngine:
    def __init__(self):
        download_models()
        self.detector = cv2.FaceDetectorYN.create(str(MODELS_DIR / "yunet.onnx"), "", (320, 320), 0.8)
        self.recognizer = cv2.FaceRecognizerSF.create(str(MODELS_DIR / "sface.onnx"), "")

    @staticmethod
    def _shrink(img):
        h, w = img.shape[:2]
        scale = MAX_SIDE / max(h, w)
        if scale < 1:
            img = cv2.resize(img, (int(w * scale), int(h * scale)))
        return img

    def embeddings(self, img) -> np.ndarray:
        """Return an (n, 128) array of L2-normalised face embeddings."""
        img = self._shrink(img)
        h, w = img.shape[:2]
        self.detector.setInputSize((w, h))
        _, faces = self.detector.detect(img)
        if faces is None:
            return np.zeros((0, 128), np.float32)
        feats = []
        for face in faces:
            aligned = self.recognizer.alignCrop(img, face)
            f = self.recognizer.feature(aligned).flatten()
            feats.append(f / np.linalg.norm(f))
        return np.array(feats, np.float32)

    def embeddings_from_bytes(self, data: bytes) -> np.ndarray:
        return self.embeddings(self.decode(data))

    @staticmethod
    def decode(data: bytes):
        img = cv2.imdecode(np.frombuffer(data, np.uint8), cv2.IMREAD_COLOR)
        if img is None:
            raise ValueError("Not an image")
        return img

    def selfie(self, img):
        """Embedding of the selfie's biggest face, plus a retake reason if it's too small or blurry."""
        img = self._shrink(img)
        h, w = img.shape[:2]
        self.detector.setInputSize((w, h))
        _, faces = self.detector.detect(img)
        if faces is None:
            return None, "No face found. Face the camera in good light and try again."
        face = max(faces, key=lambda f: f[2] * f[3])
        x, y, fw, fh = (int(v) for v in face[:4])
        if fw < MIN_FACE_PX:
            return None, "Your face is too small in the photo. Hold the phone closer and try again."
        crop = cv2.cvtColor(img[max(0, y):y + fh, max(0, x):x + fw], cv2.COLOR_BGR2GRAY)
        crop = cv2.resize(crop, (160, max(1, int(160 * fh / fw))))
        if cv2.Laplacian(crop, cv2.CV_64F).var() < MIN_SHARPNESS:
            return None, ("Your selfie looks blurry or smoothed by a filter. Turn off beauty mode or filters, "
                          "hold still in good light, and try again.")
        f = self.recognizer.feature(self.recognizer.alignCrop(img, face)).flatten()
        return f / np.linalg.norm(f), None
