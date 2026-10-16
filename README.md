<p align="center"><img src="docs/logo.svg" width="96" alt="Lens It logo"></p>

# Lens It

**Find yourself in every moment.**

[![CI](https://github.com/LovableLynx/lensit/actions/workflows/ci.yml/badge.svg)](https://github.com/LovableLynx/lensit/actions/workflows/ci.yml) [![Release](https://github.com/LovableLynx/lensit/actions/workflows/release.yml/badge.svg)](https://github.com/LovableLynx/lensit/actions/workflows/release.yml)

Offline, local-first event photo finder. A photographer indexes a shoot on their laptop; guests at the venue scan a QR code, take a selfie, and get every photo they're in — **without the internet**.

- Selfies are matched in memory on the photographer's laptop and never saved or sent online.
- Face data auto-deletes when the event expires (default 72 h), or immediately with `purge`.
- Runs on CPU (tested on an 8 GB i5 laptop).

## Models (open-source)
| Task | Model | License |
|---|---|---|
| Face detection | YuNet (opencv_zoo) | Apache-2.0 |
| Face recognition | SFace (opencv_zoo) | Apache-2.0 |

## Quick start (Windows, no coding)
Download **LensIt.exe** from the [latest release](https://github.com/LovableLynx/lensit/releases/latest) and double-click it. No Python needed. If Windows shows "Windows protected your PC", click **More info → Run anyway** (the app isn't code-signed yet).

### Or run from source with the launcher
1. Install Python 3.11+ from python.org and tick **Add python.exe to PATH**.
2. Download this repo as a ZIP and extract it.
3. Double-click **`Start Lens It.bat`**. The first run sets everything up (needs internet once), then the setup screen opens in your browser.

## Run (command line)
```bash
python -m venv .venv && .venv/Scripts/pip install -r requirements.txt   # Windows
python -m lensit index "C:/path/to/event/photos" --expire-hours 72
python -m lensit serve        # prints the guest URL; QR at /qr.png
python -m lensit purge        # delete face data now
```
Guests must be on the same Wi-Fi/hotspot as the laptop.

## Website
Landing page: https://lovablelynx.github.io/lensit/ (source in `docs/`).

## Development
```bash
pip install --require-hashes -r requirements.txt
pip install -r requirements-dev.txt
python -m pytest -q tests
```
Every push runs the tests on GitHub Actions. Pushing a tag like `v0.2.0` makes GitHub test, build and publish `LensIt.exe` with its SHA-256 checksum and a signed build attestation, so anyone can verify the file was built from this repo:
```bash
gh attestation verify LensIt.exe --repo LovableLynx/lensit
```

## License
Copyright (C) 2026 WANDERCOIL (Oluwadarasimi Olowe).

Lens It is free, open-source software under the **GNU Affero General Public License v3.0** (see [LICENSE](LICENSE)). You can use, study, change and share it. If you distribute it, or run a modified version as a service, you must publish your full source code under the same licence and keep this copyright notice. For a commercial licence without these terms, contact WANDERCOIL.

Face models: YuNet and SFace by OpenCV, Apache-2.0. Fonts: Plus Jakarta Sans and Space Grotesk, SIL Open Font License.

**Trademarks:** Lens It and the Lens It and WANDERCOIL logos are trademarks of WANDERCOIL. The open-source licence covers the code only, not the names or logos. Forks must use a different name and logo.

---
Lens It is a **WANDERCOIL** product.
