"""
WARISCRYPT - USB Launcher Companion
Mendeteksi keberadaan Flashdisk WARISCRYPT berotorisasi secara otomatis
dan membuka aplikasi web aman di browser.
"""

import os
import sys
import time
import json
import webbrowser
from pathlib import Path
import urllib.request
import urllib.error

API_VERIFY_URL = os.getenv("WARISCRYPT_API_URL", "http://localhost:8000/api/usb/verify")
WEB_APP_URL = os.getenv("WARISCRYPT_WEB_URL", "http://localhost:8000/static/index.html")

def find_usb_key_file() -> tuple[Path | None, str | None]:
    """
    Search for 'wariscrypt.key' in removable storage drives or current directory.
    """
    candidate_paths = []
    
    # Check Windows drive letters
    if sys.platform == "win32":
        import string
        from ctypes import windll
        
        bitmask = windll.kernel32.GetLogicalDrives()
        for letter in string.ascii_uppercase:
            if bitmask & 1:
                drive = f"{letter}:\\"
                # Check for key file
                p = Path(drive) / "wariscrypt.key"
                candidate_paths.append(p)
            bitmask >>= 1
            
    # Also check local simulation folder / current directory
    candidate_paths.append(Path.cwd() / "wariscrypt.key")
    candidate_paths.append(Path.cwd() / "usb_drive" / "wariscrypt.key")
    
    for path in candidate_paths:
        try:
            if path.exists() and path.is_file():
                content = path.read_text(encoding="utf-8").strip()
                return path, content
        except Exception:
            continue
            
    return None, None

def verify_key_with_backend(key_content: str) -> dict:
    """Send verification request to WARISCRYPT backend API."""
    payload = json.dumps({"device_fingerprint": key_content}).encode("utf-8")
    req = urllib.request.Request(
        API_VERIFY_URL,
        data=payload,
        headers={"Content-Type": "application/json"}
    )
    try:
        with urllib.request.urlopen(req, timeout=5) as response:
            res_data = json.loads(response.read().decode("utf-8"))
            return res_data
    except urllib.error.URLError as e:
        return {"authenticated": False, "message": f"Tidak dapat menghubungi server backend: {e}"}

def run_cli():
    print("=" * 60)
    print("   WARISCRYPT - USB HARDWARE LAUNCHER")
    print("=" * 60)
    print(f"Target Server : {API_VERIFY_URL}")
    print(f"Web App URL   : {WEB_APP_URL}")
    print("\nMenunggu USB Flashdisk terpasang (mencari 'wariscrypt.key')...")
    print("Tekan Ctrl+C untuk keluar.\n")
    
    detected = False
    while not detected:
        key_path, key_content = find_usb_key_file()
        if key_path and key_content:
            print(f"[+] Ditemukan kunci otorisasi di: {key_path}")
            print("[*] Melakukan verifikasi kriptografis ke backend server...")
            
            res = verify_key_with_backend(key_content)
            if res.get("authenticated"):
                print("[SUCCESS] " + res.get("message", "Autentikasi Berhasil!"))
                print(f"Perangkat : {res.get('device_name')}")
                print(f"Pemilik   : {res.get('owner_username')}")
                print("\n[>>>] Membuka WARISCRYPT Web Application di default browser...")
                webbrowser.open(WEB_APP_URL)
                detected = True
                break
            else:
                print(f"[GAGAL] {res.get('message', 'Autentikasi perangkat gagal')}")
        time.sleep(2)

def run_gui():
    import tkinter as tk
    from tkinter import ttk, messagebox, filedialog
    
    root = tk.Tk()
    root.title("WARISCRYPT - USB Launcher")
    root.geometry("520x420")
    root.configure(bg="#0f172a")
    root.resizable(False, False)
    
    # Title
    lbl_title = tk.Label(
        root, 
        text="WARISCRYPT", 
        font=("Cinzel", 20, "bold"), 
        fg="#c5a880", 
        bg="#0f172a"
    )
    lbl_title.pack(pady=(20, 5))
    
    lbl_sub = tk.Label(
        root, 
        text="Hardware USB Security Key Launcher", 
        font=("Inter", 10), 
        fg="#94a3b8", 
        bg="#0f172a"
    )
    lbl_sub.pack(pady=(0, 20))
    
    # Status Frame
    frame = tk.Frame(root, bg="#1e293b", padx=20, pady=20, relief="groove", bd=1)
    frame.pack(fill="x", padx=30, pady=10)
    
    status_var = tk.StringVar(value="Status: Siap mendeteksi Flashdisk...")
    lbl_status = tk.Label(
        frame, 
        textvariable=status_var, 
        font=("Inter", 11), 
        fg="#e2e8f0", 
        bg="#1e293b",
        wraplength=420
    )
    lbl_status.pack(pady=10)
    
    progress = ttk.Progressbar(frame, mode="indeterminate", length=300)
    progress.pack(pady=5)
    
    def check_usb_device():
        key_path, key_content = find_usb_key_file()
        if key_path and key_content:
            status_var.set(f"Terdeteksi: {key_path.name}\nMemvalidasi dengan backend...")
            root.update()
            
            res = verify_key_with_backend(key_content)
            if res.get("authenticated"):
                status_var.set(f"VERIFIKASI BERHASIL!\nPerangkat: {res.get('device_name')}\nPemilik: {res.get('owner_username')}")
                progress.stop()
                messagebox.showinfo("Autentikasi Sukses", f"Perangkat terverifikasi!\nMembuka portal {res.get('owner_username')}...")
                webbrowser.open(WEB_APP_URL)
            else:
                status_var.set(f"VERIFIKASI GAGAL: {res.get('message')}")
                progress.stop()
        else:
            status_var.set("Kunci 'wariscrypt.key' belum terdeteksi pada drive USB manapun.\nSilakan colokkan flashdisk Anda.")
            progress.stop()
            
    def manual_browse():
        f = filedialog.askopenfilename(
            title="Pilih File wariscrypt.key",
            filetypes=[("WARISCRYPT Key File", "*.key"), ("All Files", "*.*")]
        )
        if f:
            content = Path(f).read_text(encoding="utf-8").strip()
            progress.start(10)
            status_var.set("Memverifikasi file kunci yang dipilih...")
            root.update()
            
            res = verify_key_with_backend(content)
            progress.stop()
            if res.get("authenticated"):
                status_var.set(f"VERIFIKASI BERHASIL!\nPerangkat: {res.get('device_name')}\nPemilik: {res.get('owner_username')}")
                messagebox.showinfo("Sukses", f"Autentikasi berhasil untuk {res.get('owner_username')}")
                webbrowser.open(WEB_APP_URL)
            else:
                status_var.set(f"GAGAL: {res.get('message')}")
                messagebox.showerror("Gagal", res.get("message"))
                
    btn_scan = tk.Button(
        root, 
        text="Scan Drive Sekarang", 
        font=("Inter", 11, "bold"), 
        bg="#c5a880", 
        fg="#0f172a", 
        activebackground="#b39263",
        padx=15, 
        pady=8, 
        command=lambda: [progress.start(10), check_usb_device()]
    )
    btn_scan.pack(pady=10)
    
    btn_browse = tk.Button(
        root, 
        text="Pilih File Kunci Manual (.key)", 
        font=("Inter", 9), 
        bg="#334155", 
        fg="#cbd5e1", 
        command=manual_browse
    )
    btn_browse.pack(pady=5)
    
    root.mainloop()

if __name__ == "__main__":
    if "--cli" in sys.argv or os.getenv("HEADLESS"):
        run_cli()
    else:
        try:
            run_gui()
        except Exception:
            run_cli()
