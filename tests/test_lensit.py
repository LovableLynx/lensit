"""End-to-end checks for Lens It: model integrity, face matching, privacy rules and the guest API."""
import importlib
import urllib.request
from pathlib import Path

import pytest

SAMPLES = "https://raw.githubusercontent.com/opencv/opencv/4.x/samples/data/"


@pytest.fixture(scope="session")
def photos(tmp_path_factory):
    """Two public OpenCV sample photos with one face each."""
    folder = tmp_path_factory.mktemp("event")
    for name in ("lena.jpg", "messi5.jpg"):
        urllib.request.urlretrieve(SAMPLES + name, folder / name)
    return folder


@pytest.fixture()
def data_dir(tmp_path, monkeypatch):
    """Keep every test's face index in a throwaway folder."""
    from lensit import index
    monkeypatch.setattr(index, "DATA_DIR", tmp_path / "data")
    return tmp_path / "data"


def test_models_pass_checksum():
    from lensit.faces import download_models
    download_models()  # raises if any model file doesn't match its SHA-256


def test_tampered_model_is_refused(tmp_path, monkeypatch):
    from lensit import faces
    for name in faces.MODELS:
        (tmp_path / name).write_bytes((faces.MODELS_DIR / name).read_bytes() + b"x")
    monkeypatch.setattr(faces, "MODELS_DIR", tmp_path)
    with pytest.raises(RuntimeError, match="modified"):
        faces.download_models()


def test_selfie_matches_only_the_right_photo(photos, data_dir):
    import cv2
    from lensit.faces import FaceEngine
    from lensit.index import EventIndex, build_index
    build_index(str(photos), expire_hours=1)
    idx = EventIndex()
    assert len(idx.photos) == 2 and len(idx.vecs) == 2

    engine = FaceEngine()
    for name in ("lena.jpg", "messi5.jpg"):
        # A mirrored, darker copy stands in for a different shot of the same person.
        img = cv2.flip(cv2.imread(str(photos / name)), 1)
        selfie = engine.embeddings(cv2.convertScaleAbs(img, alpha=0.7))[0]
        matches = idx.match(selfie)
        assert [Path(idx.photos[m]).name for m in matches] == [name]


def test_purge_deletes_face_data(photos, data_dir):
    from lensit.index import build_index, purge
    build_index(str(photos), expire_hours=1)
    assert data_dir.exists()
    purge()
    assert not data_dir.exists()


def test_empty_folder_is_rejected(tmp_path, data_dir):
    from lensit.index import build_index
    with pytest.raises(ValueError):
        build_index(str(tmp_path), expire_hours=1)


@pytest.fixture()
def client(photos, data_dir):
    from fastapi.testclient import TestClient
    from lensit.index import build_index
    build_index(str(photos), expire_hours=1, event_name="CI Party")
    server = importlib.reload(importlib.import_module("lensit.server"))
    return TestClient(server.app)


def test_setup_is_blocked_for_other_devices(client):
    # TestClient connects from "testclient", i.e. not the laptop itself.
    for path in ("/setup", "/setup/status"):
        assert client.get(path).status_code == 403
    assert client.post("/setup/purge").status_code == 403


def test_guest_page_shows_event_and_consent(client):
    html = client.get("/").text
    assert "CI Party" in html and 'id="agree"' in html and "privacy notice" in html


def test_search_requires_consent(client, photos):
    r = client.post("/search", files={"selfie": ("s.jpg", (photos / "lena.jpg").read_bytes(), "image/jpeg")})
    assert r.status_code == 400


def test_search_preview_and_download(client, photos):
    # A clear, close face works as a selfie (an action shot with a tiny, blurred face is refused).
    r = client.post("/search", data={"consent": "yes"},
                    files={"selfie": ("s.jpg", (photos / "lena.jpg").read_bytes(), "image/jpeg")})
    assert r.status_code == 200 and r.json()["count"] == 1
    token = r.json()["token"]
    assert client.get(f"/preview/{token}/0").headers["content-type"] == "image/jpeg"
    assert client.get(f"/download/{token}").headers["content-type"] == "application/zip"
    assert client.get("/preview/not-a-token/0").status_code == 404


def test_non_image_is_rejected(client):
    r = client.post("/search", data={"consent": "yes"}, files={"selfie": ("x.txt", b"hello", "text/plain")})
    assert r.status_code == 400


def test_blurry_selfie_is_refused(photos):
    import cv2
    from lensit.faces import FaceEngine
    engine = FaceEngine()
    img = cv2.imread(str(photos / "lena.jpg"))
    me, retake = engine.selfie(img)
    assert me is not None and retake is None
    blurred = cv2.GaussianBlur(img, (0, 0), 2.5)  # like a beauty filter or heavy compression
    me, retake = engine.selfie(blurred)
    assert me is None and "blurry" in retake  # sharpness ~6, below the limit of 8


def test_search_reports_sure_and_maybe(client, photos):
    r = client.post("/search", data={"consent": "yes"},
                    files={"selfie": ("s.jpg", (photos / "lena.jpg").read_bytes(), "image/jpeg")})
    j = r.json()
    assert r.status_code == 200 and j["count"] == len(j["sure"]) and j["strong"] == sum(j["sure"])


def test_single_photo_and_partial_download(client, photos):
    import io
    import zipfile
    r = client.post("/search", data={"consent": "yes"},
                    files={"selfie": ("s.jpg", (photos / "lena.jpg").read_bytes(), "image/jpeg")})
    token = r.json()["token"]
    one = client.get(f"/photo/{token}/0")
    assert one.status_code == 200 and "attachment" in one.headers["content-disposition"]
    z = zipfile.ZipFile(io.BytesIO(client.get(f"/download/{token}?only=0").content))
    assert len(z.namelist()) == 1
    assert client.get(f"/photo/{token}/99").status_code == 404


@pytest.mark.parametrize("angle", [90, -90, 180, 45, 135])
def test_rotated_photo_still_matches(photos, angle):
    import cv2
    from lensit.faces import FaceEngine
    engine = FaceEngine()
    img = cv2.imread(str(photos / "lena.jpg"))
    me = engine.embeddings(img)[0]
    turned = engine.embeddings(engine._rotate(img, angle))
    assert len(turned) == 1 and float(turned[0] @ me) > 0.45
