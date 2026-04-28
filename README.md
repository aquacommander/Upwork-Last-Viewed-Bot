# Upwork Last Viewed Monitor

A Windows system-tray bot that monitors Upwork job postings and sends a native
Windows notification the moment a client views your proposal (within the last
60 seconds).

---

## Quick Start

### 1. Install Python (if not already installed)
Download from https://www.python.org/downloads/ — make sure to tick
**"Add Python to PATH"** during setup.

### 2. Edit credentials (optional — you can also enter them in the UI)
Open `upwork_monitor.py` and change lines ~25-26:
```python
YOUR_EMAIL    = "your_email@example.com"
YOUR_PASSWORD = "your_password_here"
```

### 3. Run directly (no EXE needed)
```bash
pip install -r requirements.txt
python upwork_monitor.py
```

### 4. Build a standalone EXE
Double-click **`build_exe.bat`** — it installs all dependencies and produces
`dist\UpworkMonitor.exe`.

---

## How to Use

1. **Double-click** `UpworkMonitor.exe` (or run the Python script).
2. The app starts **silently in the system tray** (clock area, bottom-right).
3. **Right-click the tray icon** to open the menu:
   - **Settings** — opens the configuration window
   - **Start / Stop Monitoring** — toggle the bot
   - **Check Now** — one-time manual check
   - **View Log File** — open the activity log
   - **Exit** — close the app
4. In the Settings window:
   - Enter your **Upwork email & password**
   - Paste **Job IDs** (or full job URLs) and click **Add**
   - Set the **check interval** (default 30 s)
   - Click **▶ Start Monitoring**

---

## Finding a Job ID

From a job URL like:
```
https://www.upwork.com/jobs/~021234567890abcdef
```
The Job ID is everything after `~`:  `021234567890abcdef`

You can paste the full URL into the Job ID field — the app will extract the ID
automatically.

---

## Notification Example

```
┌──────────────────────────────────────────┐
│  🔔 Upwork Client Alert!                 │
├──────────────────────────────────────────┤
│  Job ~703697033 viewed 45 seconds ago!   │
│                              [Dismiss]   │
└──────────────────────────────────────────┘
```

---

## Auto-start with Windows

**Method 1 — Startup folder:**
1. Press `Win + R`, type `shell:startup`, press Enter.
2. Copy `UpworkMonitor.exe` into that folder.

**Method 2 — Task Scheduler:**
1. Open Task Scheduler → Create Basic Task.
2. Trigger: *When the computer starts*.
3. Action: Start a program → select `UpworkMonitor.exe`.

---

## Files

| File | Purpose |
|------|---------|
| `upwork_monitor.py` | Main application source |
| `requirements.txt` | Python dependencies |
| `build_exe.bat` | One-click EXE builder |
| `upwork_config.json` | Auto-created — saves your watchlist |
| `upwork_monitor_log.txt` | Auto-created — activity log |

---

## Troubleshooting

| Problem | Fix |
|---------|-----|
| Login fails | Check email/password; Upwork may require CAPTCHA on first login — run without `--headless` to see the browser |
| No notifications | Make sure Windows Focus Assist is off; try `winotify` or `win10toast` |
| EXE too large | Normal (~80-120 MB) — it bundles Python + Chrome driver |
| "No module" error | Run `pip install -r requirements.txt` again |
| Chrome not found | Install Google Chrome from https://www.google.com/chrome |

---

## Removing Headless Mode (to see the browser)

In `upwork_monitor.py`, comment out this line in the `login()` method:
```python
# opts.add_argument("--headless=new")
```
This lets you watch the login process and handle any CAPTCHA manually.
