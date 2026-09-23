"""Chay LSteven Cockpit nhu mot tien trinh nen, doc lap voi phien Claude Code.

Dung script nay (khong phai `uvicorn api:app` truc tiep) khi dang ky Windows
Task Scheduler — no chuyen huong stdout/stderr ra file log truoc khi nap
uvicorn, nen chay duoc voi pythonw.exe (khong cua so console) ma van giu
duoc log de debug khi can.

Xem README muc "Chay ben, khong phu thuoc Claude Code" de biet cach dang ky.
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
LOG_FILE = ROOT / "server.log"

# Mo som, truoc khi import uvicorn/api — de bat duoc ca loi import neu co.
sys.stdout = sys.stderr = open(LOG_FILE, "a", buffering=1, encoding="utf-8")
sys.path.insert(0, str(ROOT))

import uvicorn  # noqa: E402
from api import app  # noqa: E402

if __name__ == "__main__":
    print("\n" + "=" * 60, flush=True)
    print("LSteven Cockpit — khoi dong nen", flush=True)
    print("=" * 60, flush=True)
    uvicorn.run(app, host="127.0.0.1", port=8787, log_level="info")
