"""Face detection (YuNet) and recognition (SFace) via OpenCV. Both models are Apache-2.0 (opencv_zoo)."""
import urllib.request
from pathlib import Path

import cv2
import numpy as np

MODELS_DIR = Path(__file__).resolve().parent.parent / "models"
MODELS = {
    "yunet.onnx": "https://github.com/opencv/opencv_zoo/raw/main/models/face_detection_yunet/face_detection_yunet_2023mar.onnx",
    "sface.onnx": "https://github.com/opencv/opencv_zoo/raw/main/models/face_recognition_sface/face_recognition_sface_2021dec.onnx",
}
# Cosine-similarity threshold recommended by OpenCV for SFace.
MATCH_THRESHOLD = 0.363
MAX_SIDE = 1280  # downscale big camera photos; keeps an 8 GB laptop happy


def download_models():
    MODELS_DIR.mkdir(exist_ok=True)
    for name, url in MODELS.items():
        dest = MODELS_DIR / name
        if not dest.exists():
            print(f"Downloading {name} ...")
            urllib.request.urlretrieve(url, dest)


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
        img = cv2.imdecode(np.frombuffer(data, np.uint8), cv2.IMREAD_COLOR)
        if img is None:
            raise ValueError("Not an image")
        return self.embeddings(img)
