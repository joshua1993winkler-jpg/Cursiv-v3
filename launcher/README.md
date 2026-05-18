# Cursiv v3.0 Desktop Launcher

This folder contains the production-ready desktop launcher for Cursiv v3.0.

## Quick Start (Windows)

1. Double-click `launch_cursiv.bat`
2. The clean GUI window will appear with no black terminal.
3. All background services (Guardian, Tracker, etc.) run silently.

## Alternative Entry Points

- `python main.py` — Standard Python launch
- `pythonw hide_console.pyw` — Completely hidden console version (recommended for production)

## What You See

- Clean professional window with four main buttons
- System tray icon
- Real-time status of background services
- No terminal windows ever pop up

## Notes

- Requires Python 3.10+ and the packages in `requirements.txt`
- Install dependencies first: `pip install -r requirements.txt`
- This launcher is designed to be bundled into a single executable later using PyInstaller or similar tools.

## Future

This launcher will eventually support:
- Full Cursiv GUI
- Direct chat terminal
- Status dashboard
- Guardian security panel

All background systems stay hidden.