# LocalLens

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
1. Install Python 3.11+ from python.org and tick **Add python.exe to PATH**.
2. Download this repo as a ZIP and extract it.
3. Double-click **`Start LocalLens.bat`**. The first run sets everything up (needs internet once), then the setup screen opens in your browser.

## Run (command line)
```bash
python -m venv .venv && .venv/Scripts/pip install -r requirements.txt   # Windows
python -m locallens index "C:/path/to/event/photos" --expire-hours 72
python -m locallens serve        # prints the guest URL; QR at /qr.png
python -m locallens purge        # delete face data now
```
Guests must be on the same Wi-Fi/hotspot as the laptop.

## Website
Landing page: https://lovablelynx.github.io/locallens/ (source in `docs/`).
