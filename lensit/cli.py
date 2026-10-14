import argparse


def main():
    p = argparse.ArgumentParser(prog="lensit", description="Offline event photo finder")
    sub = p.add_subparsers(dest="cmd", required=True)
    i = sub.add_parser("index", help="index a folder of event photos")
    i.add_argument("folder")
    i.add_argument("--expire-hours", type=float, default=72, help="auto-delete face data after this (default 72)")
    s = sub.add_parser("serve", help="start the guest page on the local network")
    s.add_argument("--port", type=int, default=8000)
    sub.add_parser("purge", help="delete all face data now")
    a = p.parse_args()

    if a.cmd == "index":
        from .index import build_index
        build_index(a.folder, a.expire_hours)
    elif a.cmd == "purge":
        from .index import purge
        purge()
    else:
        import os
        os.environ["LENSIT_PORT"] = str(a.port)
        import uvicorn
        import qrcode
        from .server import app, guest_url
        url = guest_url()
        print(f"Photographer: open http://localhost:{a.port}/setup on this laptop")
        q = qrcode.QRCode()
        q.add_data(url)
        try:
            q.print_ascii(invert=True)
        except UnicodeEncodeError:  # older Windows consoles
            pass
        print(f"Guests: connect to this Wi-Fi and open {url}  (printable QR: {url}qr.png)")
        uvicorn.run(app, host="0.0.0.0", port=a.port)


if __name__ == "__main__":
    main()
