"""
WARISCRYPT - Main Application Runner
Menjalankan FastAPI backend server dan menyajikan antarmuka frontend secara terintegrasi.
"""

import os
import sys
import subprocess
import webbrowser
import time
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
BACKEND_DIR = BASE_DIR / "backend"

def main():
    print("=" * 65)
    print("       WARISCRYPT - SECURE DIGITAL INHERITANCE SYSTEM")
    print("=" * 65)
    
    # 1. Ensure database seed exists
    db_file = BACKEND_DIR / "wariscrypt.db"
    if not db_file.exists():
        print("[*] Menginisialisasi basis data awal & membuat akun demo...")
        subprocess.run([sys.executable, str(BASE_DIR / "database" / "seed_demo.py")], check=True)
    else:
        print("[+] Basis data terdeteksi.")

    print("\n[*] Menjalankan server aplikasi di http://localhost:8000 ...")
    print("    - Web Portal    : http://localhost:8000/static/index.html")
    print("    - API Docs      : http://localhost:8000/api/docs")
    print("    - USB Launcher  : python usb_launcher/usb_launcher.py")
    print("\nTekan Ctrl+C untuk menghentikan server.\n")

    # Launch browser after a brief delay
    def open_browser():
        time.sleep(1.5)
        webbrowser.open("http://localhost:8000/static/index.html")

    import threading
    threading.Thread(target=open_browser, daemon=True).start()

    # Run Uvicorn
    import uvicorn
    uvicorn.run(
        "backend.app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=False
    )

if __name__ == "__main__":
    main()
