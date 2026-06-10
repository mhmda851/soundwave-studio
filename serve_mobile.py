"""
خادم محلي لتجربة تطبيق الموبايل (PWA) على الهاتف والكمبيوتر.

التشغيل:
    python serve_mobile.py

ثم افتح على الموبايل (نفس شبكة الواي فاي):
    http://<IP-الكمبيوتر>:8080/mobile/

للتثبيت على الموبايل:
  Android Chrome → القائمة ⋮ → «إضافة إلى الشاشة الرئيسية»
  iPhone Safari  → مشاركة ↑ → «Add to Home Screen»
"""

import socket
import sys
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

PORT = 8080
ROOT = Path(__file__).parent


class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(ROOT), **kwargs)

    def end_headers(self):
        self.send_header("Cache-Control", "no-cache")
        super().end_headers()


def local_ip() -> str:
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except OSError:
        return "127.0.0.1"


def main():
    ip = local_ip()
    url = f"http://{ip}:{PORT}/mobile/"
    print("=" * 50)
    print("  SoundWave Mobile — Local Server")
    print("=" * 50)
    print(f"  PC:     http://127.0.0.1:{PORT}/mobile/")
    print(f"  Mobile: {url}")
    print()
    print("  افتح الرابط على الموبايل ثم ثبّت التطبيق من المتصفح.")
    print("  اضغط Ctrl+C للإيقاف.")
    print("=" * 50)

    server = ThreadingHTTPServer(("0.0.0.0", PORT), Handler)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopped.")
        server.server_close()
        sys.exit(0)


if __name__ == "__main__":
    main()
