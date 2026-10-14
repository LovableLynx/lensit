"""Entry point for the packaged Windows app: start the server and open the setup screen."""
import threading
import time
import webbrowser

from .cli import main as cli_main


def run():
    import sys
    threading.Thread(target=lambda: (time.sleep(4), webbrowser.open("http://localhost:8000/setup")), daemon=True).start()
    print("Lens It is running. Keep this window open during the event; close it to stop.\n")
    sys.argv = ["lensit", "serve"]
    cli_main()


if __name__ == "__main__":
    run()
