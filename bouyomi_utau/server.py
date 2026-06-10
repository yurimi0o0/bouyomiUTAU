from __future__ import annotations

import argparse
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import urllib.parse
import webbrowser

from .synth import load_oto, synthesize

ROOT = Path(__file__).resolve().parents[1]
WEB = ROOT / "web"


class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(WEB), **kwargs)

    def _json(self, status: int, value: dict):
        body = json.dumps(value, ensure_ascii=False).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        params = urllib.parse.parse_qs(parsed.query)
        if parsed.path == "/api/inspect":
            try:
                path = Path(params.get("voicebank", [""])[0]).expanduser()
                entries = load_oto(path)
                self._json(200, {"name": path.name, "sounds": len(entries), "ready": bool(entries)})
            except Exception as exc:
                self._json(400, {"error": str(exc)})
            return
        if parsed.path == "/api/talk":
            try:
                path = Path(params.get("voicebank", [""])[0]).expanduser()
                text = params.get("text", [""])[0]
                speed = float(params.get("speed", ["1"])[0])
                wav, missing = synthesize(path, text, speed=speed)
                self.send_response(200)
                self.send_header("Content-Type", "audio/wav")
                self.send_header("X-Missing-Aliases", urllib.parse.quote(",".join(missing)))
                self.send_header("Content-Length", str(len(wav)))
                self.end_headers()
                self.wfile.write(wav)
            except Exception as exc:
                self._json(400, {"error": str(exc)})
            return
        super().do_GET()


def main():
    parser = argparse.ArgumentParser(description="UTAU単独音をブラウザーからしゃべらせます")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", default=50100, type=int)
    parser.add_argument("--no-browser", action="store_true")
    args = parser.parse_args()
    server = ThreadingHTTPServer((args.host, args.port), Handler)
    url = f"http://{args.host}:{args.port}"
    print(f"BouyomiUTAU Studio: {url}")
    if not args.no_browser:
        webbrowser.open(url)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
