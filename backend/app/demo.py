"""Mac-friendly, explicit synthetic demo. Normal app.main never loads these fixtures."""

import argparse
import threading
import time
import urllib.error
import urllib.request
import webbrowser

import uvicorn

from .core import ROOT, Settings
from .main import create_app


def open_when_ready(url):
    for _ in range(40):
        try:
            with urllib.request.urlopen(url + "/api/v1/health", timeout=1) as response:
                if response.status == 200:
                    webbrowser.open(url)
                    return
        except (OSError, urllib.error.URLError):
            time.sleep(0.25)


def main():
    parser = argparse.ArgumentParser(description="Synthetic demo, isolated from real career data")
    parser.add_argument("--port", type=int, default=8001)
    parser.add_argument("--no-browser", action="store_true")
    args = parser.parse_args()
    settings = Settings(
        data_dir=ROOT / "data-demo", demo_mode=True, watcher_enabled=True, http_port=args.port
    )
    app = create_app(settings)
    url = f"http://127.0.0.1:{args.port}"
    print(f"ДЕМО: вымышленные данные, игра не требуется. {url}", flush=True)
    if not args.no_browser:
        threading.Thread(target=open_when_ready, args=(url,), daemon=True).start()
    uvicorn.run(app, host="127.0.0.1", port=args.port)


if __name__ == "__main__":
    main()
