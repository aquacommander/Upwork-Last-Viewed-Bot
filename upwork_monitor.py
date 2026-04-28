# ============================================
# UPWORK LAST VIEWED MONITOR - WINDOWS TRAY APP
# Runs in system tray, sends Windows notifications
# ============================================

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
import tkinter as tk
from tkinter import messagebox, scrolledtext
import threading
import time
import re
import json
import os
import sys
from datetime import datetime
import pystray
from PIL import Image, ImageDraw
from pathlib import Path

# ============================================
# CONFIGURATION  — CHANGE THESE BEFORE RUNNING
# ============================================
CONFIG_FILE = "upwork_config.json"
LOG_FILE    = "upwork_monitor_log.txt"

YOUR_EMAIL    = "your_email@example.com"   # ← CHANGE THIS
YOUR_PASSWORD = "your_password_here"        # ← CHANGE THIS

CHECK_INTERVAL = 30   # seconds between checks
AUTO_START     = False # start monitoring automatically on launch

# ============================================
# WINDOWS NOTIFICATION HANDLER
# ============================================
class WindowsNotifier:
    def __init__(self):
        self._backend = None
        self._init_backend()

    def _init_backend(self):
        # Try winotify first (best quality)
        try:
            from winotify import Notification, audio as _audio  # noqa: F401
            self._backend = "winotify"
            return
        except ImportError:
            pass
        # Fall back to win10toast
        try:
            import win10toast
            self._toaster = win10toast.ToastNotifier()
            self._backend = "win10toast"
            return
        except ImportError:
            pass
        # Last resort: plyer
        try:
            from plyer import notification as _n  # noqa: F401
            self._backend = "plyer"
        except ImportError:
            self._backend = None

    def send(self, title: str, message: str, duration: int = 5) -> bool:
        """Send a Windows native notification."""
        try:
            if self._backend == "winotify":
                from winotify import Notification, audio
                toast = Notification(
                    app_id="Upwork Monitor",
                    title=title,
                    msg=message,
                    duration="short"
                )
                toast.set_audio(audio.Default, loop=False)
                toast.show()
                return True

            elif self._backend == "win10toast":
                self._toaster.show_toast(title, message, duration=duration, threaded=True)
                return True

            elif self._backend == "plyer":
                from plyer import notification
                notification.notify(title=title, message=message, timeout=duration)
                return True

            else:
                print(f"[NOTIFY] {title}: {message}")
                return False

        except Exception as exc:
            print(f"Notification error: {exc}")
            return False


# ============================================
# CONFIGURATION MANAGER
# ============================================
class ConfigManager:
    @staticmethod
    def load() -> dict:
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, "r", encoding="utf-8") as fh:
                    return json.load(fh)
            except Exception:
                pass
        return {
            "job_ids":        [],
            "check_interval": CHECK_INTERVAL,
            "auto_start":     AUTO_START,
            "email":          YOUR_EMAIL,
        }

    @staticmethod
    def save(config: dict) -> None:
        with open(CONFIG_FILE, "w", encoding="utf-8") as fh:
            json.dump(config, fh, indent=2)


# ============================================
# CORE MONITOR BOT
# ============================================
class UpworkMonitorBot:
    def __init__(self, log_callback=None, alert_callback=None):
        self.driver         = None
        self.log_callback   = log_callback
        self.alert_callback = alert_callback
        self.is_running     = False
        self.is_logged_in   = False

    # ── logging ──────────────────────────────
    def log(self, message: str) -> None:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        formatted = f"[{timestamp}] {message}"
        try:
            with open(LOG_FILE, "a", encoding="utf-8") as fh:
                fh.write(formatted + "\n")
        except Exception:
            pass
        if self.log_callback:
            self.log_callback(formatted)
        print(formatted)

    # ── helpers ──────────────────────────────
    @staticmethod
    def _seconds_from_text(text: str):
        """Convert 'X minutes ago' style text to seconds."""
        if not text:
            return None
        text = text.lower()
        for pattern, unit in [
            (r"(\d+)\s*second", "second"),
            (r"(\d+)\s*minute", "minute"),
            (r"(\d+)\s*hour",   "hour"),
            (r"(\d+)\s*day",    "day"),
        ]:
            m = re.search(pattern, text)
            if m:
                n = int(m.group(1))
                return {"second": n, "minute": n * 60, "hour": n * 3600, "day": n * 86400}[unit]
        return None

    # ── login ────────────────────────────────
    def login(self, email: str, password: str) -> bool:
        self.log("🔐 Logging into Upwork...")
        opts = Options()
        opts.add_argument("--disable-blink-features=AutomationControlled")
        opts.add_experimental_option("excludeSwitches", ["enable-automation"])
        opts.add_experimental_option("useAutomationExtension", False)
        opts.add_argument("--headless=new")          # remove to see the browser
        opts.add_argument("--no-sandbox")
        opts.add_argument("--disable-dev-shm-usage")

        try:
            service = Service(ChromeDriverManager().install())
            self.driver = webdriver.Chrome(service=service, options=opts)
            self.driver.get("https://www.upwork.com/ab/account-security/login")
            time.sleep(3)

            # Enter email
            email_input = WebDriverWait(self.driver, 15).until(
                EC.presence_of_element_located((By.ID, "login_username"))
            )
            email_input.clear()
            email_input.send_keys(email)
            self.driver.find_element(By.ID, "login_password_continue").click()
            time.sleep(2)

            # Enter password
            pwd_input = WebDriverWait(self.driver, 15).until(
                EC.presence_of_element_located((By.ID, "login_password"))
            )
            pwd_input.clear()
            pwd_input.send_keys(password)
            self.driver.find_element(By.ID, "login_control_continue").click()
            time.sleep(5)

            self.log("✅ Login successful!")
            self.is_logged_in = True
            return True

        except Exception as exc:
            self.log(f"❌ Login failed: {exc}")
            return False

    # ── single job check ─────────────────────
    def check_job(self, job_id: str):
        """Returns (seconds_ago, alerted)."""
        short = job_id[-12:] if len(job_id) > 12 else job_id
        try:
            self.driver.get(f"https://www.upwork.com/jobs/~{job_id}")
            time.sleep(2)
            page = self.driver.page_source

            for pattern in [
                r"Last viewed by client[:\s]+(\d+)\s*(second|minute|hour)",
                r"viewed\s+(\d+)\s*(second|minute|hour)\s+ago",
                r"Client viewed\s+(\d+)\s*(second|minute|hour)\s+ago",
            ]:
                m = re.search(pattern, page, re.IGNORECASE)
                if m:
                    n    = int(m.group(1))
                    unit = m.group(2).lower()
                    secs = {"second": n, "minute": n * 60, "hour": n * 3600}.get(unit)
                    if secs is None:
                        continue

                    display = f"{secs}s" if secs < 60 else f"{secs // 60}m"
                    self.log(f"📋 ~{short}: last viewed {display} ago")

                    if 1 <= secs <= 60:
                        self.log(f"🔔 ALERT! ~{short} viewed {secs}s ago!")
                        if self.alert_callback:
                            self.alert_callback(job_id, secs)
                        return secs, True

                    return secs, False

            self.log(f"📋 ~{short}: no 'last viewed' data found")
            return None, False

        except Exception as exc:
            self.log(f"❌ ~{short}: {str(exc)[:60]}")
            return None, False

    # ── monitoring loop ──────────────────────
    def start_monitoring(self, job_ids: list, stop_event: threading.Event,
                         check_interval: int) -> None:
        self.is_running = True
        self.log(f"🟢 Monitoring {len(job_ids)} job(s) every {check_interval}s")

        check_count = 0
        while not stop_event.is_set():
            check_count += 1
            self.log(f"\n--- Check #{check_count} @ {datetime.now().strftime('%H:%M:%S')} ---")
            for job_id in job_ids:
                if stop_event.is_set():
                    break
                self.check_job(job_id)

            # Interruptible sleep
            for _ in range(check_interval):
                if stop_event.is_set():
                    break
                time.sleep(1)

        self.is_running = False
        self.log("🔴 Monitoring stopped")

    def close(self) -> None:
        if self.driver:
            try:
                self.driver.quit()
            except Exception:
                pass
        self.log("Browser closed")


# ============================================
# TRAY ICON FACTORY
# ============================================
def _make_icon(active: bool = False) -> Image.Image:
    size  = 64
    color = "#2ecc71" if active else "#95a5a6"
    img   = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw  = ImageDraw.Draw(img)
    draw.ellipse([4, 4, size - 4, size - 4], fill=color)
    draw.text((20, 18), "U", fill="white")
    return img


# ============================================
# MAIN APPLICATION
# ============================================
class UpworkTrayApp:
    def __init__(self):
        self.config      = ConfigManager.load()
        self.watchlist   = list(self.config.get("job_ids", []))
        self.bot         = None
        self.mon_thread  = None
        self.stop_event  = None
        self.is_monitoring = False
        self.notifier    = WindowsNotifier()

        self._build_window()
        self._build_tray()

        if self.config.get("auto_start") and self.watchlist:
            self.root.after(1500, self.start_monitoring)

        self.notifier.send(
            "Upwork Monitor",
            f"Started. Watching {len(self.watchlist)} job(s).",
            duration=3,
        )

    # ── UI ───────────────────────────────────
    def _build_window(self) -> None:
        self.root = tk.Tk()
        self.root.title("Upwork Last Viewed Monitor")
        self.root.geometry("640x580")
        self.root.resizable(False, False)
        self.root.configure(bg="#f0f0f0")
        self.root.protocol("WM_DELETE_WINDOW", self._hide_window)
        self.root.withdraw()   # start hidden in tray

        # ── Header ──
        hdr = tk.Frame(self.root, bg="#2c3e50", height=50)
        hdr.pack(fill="x")
        tk.Label(
            hdr, text="🔍  Upwork Last Viewed Monitor",
            font=("Segoe UI", 13, "bold"), fg="white", bg="#2c3e50"
        ).pack(pady=12)

        # ── Credentials ──
        cred_frame = tk.LabelFrame(
            self.root, text="  🔑  Credentials  ",
            font=("Segoe UI", 9, "bold"), bg="#f0f0f0", padx=10, pady=8
        )
        cred_frame.pack(fill="x", padx=15, pady=(10, 0))

        tk.Label(cred_frame, text="Email:", bg="#f0f0f0", width=10, anchor="w").grid(row=0, column=0, sticky="w")
        self.email_var = tk.StringVar(value=self.config.get("email", YOUR_EMAIL))
        tk.Entry(cred_frame, textvariable=self.email_var, width=40).grid(row=0, column=1, padx=5, pady=2)

        tk.Label(cred_frame, text="Password:", bg="#f0f0f0", width=10, anchor="w").grid(row=1, column=0, sticky="w")
        self.pass_var = tk.StringVar(value="")
        tk.Entry(cred_frame, textvariable=self.pass_var, show="*", width=40).grid(row=1, column=1, padx=5, pady=2)

        # ── Interval ──
        int_frame = tk.Frame(self.root, bg="#f0f0f0")
        int_frame.pack(fill="x", padx=15, pady=4)
        tk.Label(int_frame, text="Check every (sec):", bg="#f0f0f0").pack(side="left")
        self.interval_var = tk.IntVar(value=self.config.get("check_interval", CHECK_INTERVAL))
        tk.Spinbox(int_frame, from_=10, to=300, textvariable=self.interval_var, width=6).pack(side="left", padx=5)

        # ── Job ID input ──
        add_frame = tk.LabelFrame(
            self.root, text="  ➕  Add Job  ",
            font=("Segoe UI", 9, "bold"), bg="#f0f0f0", padx=10, pady=8
        )
        add_frame.pack(fill="x", padx=15, pady=(4, 0))

        tk.Label(add_frame, text="Job ID:", bg="#f0f0f0").pack(side="left")
        self.job_entry = tk.Entry(add_frame, width=38)
        self.job_entry.pack(side="left", padx=6)
        self.job_entry.bind("<Return>", lambda _e: self._add_job())
        tk.Button(
            add_frame, text="Add", command=self._add_job,
            bg="#27ae60", fg="white", width=8, relief="flat"
        ).pack(side="left")

        # ── Watchlist ──
        list_frame = tk.LabelFrame(
            self.root, text="  📋  Watchlist  ",
            font=("Segoe UI", 9, "bold"), bg="#f0f0f0", padx=10, pady=6
        )
        list_frame.pack(fill="x", padx=15, pady=(4, 0))

        sb = tk.Scrollbar(list_frame)
        sb.pack(side="right", fill="y")
        self.job_listbox = tk.Listbox(
            list_frame, yscrollcommand=sb.set,
            font=("Consolas", 10), height=5, selectmode="single"
        )
        self.job_listbox.pack(fill="x")
        sb.config(command=self.job_listbox.yview)

        btn_row = tk.Frame(list_frame, bg="#f0f0f0")
        btn_row.pack(pady=4)
        tk.Button(btn_row, text="Remove Selected", command=self._remove_job,
                  bg="#e74c3c", fg="white", relief="flat").pack(side="left", padx=4)
        tk.Button(btn_row, text="Clear All", command=self._clear_all,
                  bg="#95a5a6", fg="white", relief="flat").pack(side="left", padx=4)

        # ── Controls ──
        ctrl = tk.Frame(self.root, bg="#f0f0f0")
        ctrl.pack(pady=8)

        self.start_btn = tk.Button(
            ctrl, text="▶  Start Monitoring", command=self.start_monitoring,
            bg="#2ecc71", fg="white", width=18, relief="flat", font=("Segoe UI", 9, "bold")
        )
        self.start_btn.pack(side="left", padx=5)

        self.stop_btn = tk.Button(
            ctrl, text="⏹  Stop Monitoring", command=self.stop_monitoring,
            bg="#e74c3c", fg="white", width=18, relief="flat",
            font=("Segoe UI", 9, "bold"), state="disabled"
        )
        self.stop_btn.pack(side="left", padx=5)

        tk.Button(
            ctrl, text="🔍  Check Now", command=self._check_now,
            bg="#3498db", fg="white", width=14, relief="flat"
        ).pack(side="left", padx=5)

        # ── Status bar ──
        self.status_var = tk.StringVar(value="● Idle")
        tk.Label(
            self.root, textvariable=self.status_var,
            bg="#2c3e50", fg="white", anchor="w", padx=8
        ).pack(fill="x", side="bottom")

        # ── Log ──
        log_frame = tk.LabelFrame(
            self.root, text="  📝  Activity Log  ",
            font=("Segoe UI", 9, "bold"), bg="#f0f0f0", padx=8, pady=6
        )
        log_frame.pack(fill="both", expand=True, padx=15, pady=(0, 4))
        self.log_text = scrolledtext.ScrolledText(
            log_frame, height=7, font=("Consolas", 8),
            bg="#1e1e1e", fg="#d4d4d4", insertbackground="white"
        )
        self.log_text.pack(fill="both", expand=True)

        self._refresh_list()

    # ── log helper ───────────────────────────
    def _log_ui(self, message: str) -> None:
        def _append():
            self.log_text.insert(tk.END, message + "\n")
            self.log_text.see(tk.END)
        if self.root:
            self.root.after(0, _append)

    # ── watchlist helpers ────────────────────
    def _refresh_list(self) -> None:
        self.job_listbox.delete(0, tk.END)
        for jid in self.watchlist:
            short = jid[-12:] if len(jid) > 12 else jid
            self.job_listbox.insert(tk.END, f"  ~{short}")

    def _add_job(self) -> None:
        raw = self.job_entry.get().strip().lstrip("~").lstrip("0")
        # Accept full URL or bare ID
        m = re.search(r"~?(\w{15,})", raw)
        job_id = m.group(1) if m else raw
        if not job_id:
            messagebox.showwarning("Warning", "Enter a valid Job ID or URL.")
            return
        if job_id in self.watchlist:
            messagebox.showinfo("Info", "Already in watchlist.")
            return
        self.watchlist.append(job_id)
        self._save_config()
        self._refresh_list()
        self._log_ui(f"➕ Added: ~{job_id[-12:]}")
        self.job_entry.delete(0, tk.END)

    def _remove_job(self) -> None:
        sel = self.job_listbox.curselection()
        if not sel:
            return
        removed = self.watchlist.pop(sel[0])
        self._save_config()
        self._refresh_list()
        self._log_ui(f"❌ Removed: ~{removed[-12:]}")

    def _clear_all(self) -> None:
        if messagebox.askyesno("Confirm", "Remove all jobs from watchlist?"):
            self.watchlist.clear()
            self._save_config()
            self._refresh_list()
            self._log_ui("🗑️ Cleared all jobs")

    def _save_config(self) -> None:
        self.config["job_ids"]        = self.watchlist
        self.config["check_interval"] = self.interval_var.get()
        self.config["email"]          = self.email_var.get()
        ConfigManager.save(self.config)

    # ── monitoring ───────────────────────────
    def start_monitoring(self) -> None:
        if self.is_monitoring:
            return
        if not self.watchlist:
            messagebox.showwarning("Warning", "Add at least one Job ID first.")
            return

        email    = self.email_var.get().strip()
        password = self.pass_var.get().strip()
        if not email or not password:
            messagebox.showwarning("Warning", "Enter your Upwork email and password.")
            self._show_window()
            return

        interval = self.interval_var.get()
        self._log_ui("🟢 Starting monitoring…")
        self.status_var.set("● Connecting…")

        def _run():
            self.bot = UpworkMonitorBot(
                log_callback=self._log_ui,
                alert_callback=self._on_alert,
            )
            if not self.bot.login(email, password):
                self._log_ui("❌ Cannot start — login failed")
                self.root.after(0, lambda: self.status_var.set("● Login failed"))
                return

            self.stop_event = threading.Event()
            self.is_monitoring = True
            self.root.after(0, self._update_btn_state)
            self.root.after(0, lambda: self.status_var.set(
                f"● Monitoring {len(self.watchlist)} job(s) every {interval}s"
            ))
            self.bot.start_monitoring(self.watchlist, self.stop_event, interval)

        self.mon_thread = threading.Thread(target=_run, daemon=True)
        self.mon_thread.start()

    def stop_monitoring(self) -> None:
        if not self.is_monitoring:
            return
        self._log_ui("⏹ Stopping…")
        if self.stop_event:
            self.stop_event.set()
        if self.mon_thread:
            self.mon_thread.join(timeout=5)
        if self.bot:
            self.bot.close()
        self.is_monitoring = False
        self._update_btn_state()
        self.status_var.set("● Idle")

    def _update_btn_state(self) -> None:
        if self.is_monitoring:
            self.start_btn.config(state="disabled")
            self.stop_btn.config(state="normal")
        else:
            self.start_btn.config(state="normal")
            self.stop_btn.config(state="disabled")

    def _check_now(self) -> None:
        if not self.watchlist:
            messagebox.showwarning("Warning", "Add jobs first.")
            return
        email    = self.email_var.get().strip()
        password = self.pass_var.get().strip()
        if not email or not password:
            messagebox.showwarning("Warning", "Enter credentials first.")
            self._show_window()
            return

        self._log_ui("\n🔍 Manual check…")

        def _run():
            bot = UpworkMonitorBot(log_callback=self._log_ui, alert_callback=self._on_alert)
            if bot.login(email, password):
                for jid in self.watchlist:
                    bot.check_job(jid)
                bot.close()
            self._log_ui("✅ Manual check complete")

        threading.Thread(target=_run, daemon=True).start()

    # ── alert handler ────────────────────────
    def _on_alert(self, job_id: str, seconds_ago: int) -> None:
        short = job_id[-12:] if len(job_id) > 12 else job_id
        msg   = f"Job ~{short} was viewed {seconds_ago} second(s) ago!"
        self.notifier.send("🔔 Upwork Client Alert!", msg)
        self._log_ui(f"🔔🔔🔔 ALERT: {msg}")

    # ── tray ─────────────────────────────────
    def _build_tray(self) -> None:
        menu = pystray.Menu(
            pystray.MenuItem("⚙️  Settings",        self._show_window),
            pystray.MenuItem("📊  Status",           self._tray_status),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("▶  Start Monitoring",  self.start_monitoring,
                             enabled=lambda _: not self.is_monitoring),
            pystray.MenuItem("⏹  Stop Monitoring",   self.stop_monitoring,
                             enabled=lambda _: self.is_monitoring),
            pystray.MenuItem("🔍  Check Now",         self._check_now),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("📋  View Log File",     self._open_log),
            pystray.MenuItem("🚪  Exit",              self._exit_app),
        )
        self.tray = pystray.Icon(
            "upwork_monitor", _make_icon(False), "Upwork Monitor", menu
        )
        threading.Thread(target=self.tray.run, daemon=True).start()

    def _tray_status(self) -> None:
        state = "Active ✅" if self.is_monitoring else "Stopped ⏹"
        self.notifier.send(
            "Upwork Monitor Status",
            f"Monitoring: {state}\nJobs in watchlist: {len(self.watchlist)}"
        )

    def _show_window(self, *_args) -> None:
        self.root.deiconify()
        self.root.lift()
        self.root.focus_force()

    def _hide_window(self) -> None:
        self.root.withdraw()

    def _open_log(self) -> None:
        if os.path.exists(LOG_FILE):
            os.startfile(LOG_FILE)
        else:
            self.notifier.send("Upwork Monitor", "No log file yet.")

    def _exit_app(self) -> None:
        self.stop_monitoring()
        try:
            self.tray.stop()
        except Exception:
            pass
        self.root.quit()
        self.root.destroy()
        os._exit(0)

    # ── run ──────────────────────────────────
    def run(self) -> None:
        self.root.mainloop()


# ============================================
# ENTRY POINT
# ============================================
def _check_deps() -> bool:
    missing = []
    for pkg in ("selenium", "webdriver_manager", "pystray", "PIL"):
        try:
            __import__(pkg)
        except ImportError:
            missing.append(pkg)
    if missing:
        print(f"Missing packages: {missing}")
        print("Run:  pip install -r requirements.txt")
        return False
    return True


def main():
    if not _check_deps():
        input("Press Enter to exit…")
        return
    app = UpworkTrayApp()
    app.run()


if __name__ == "__main__":
    main()
