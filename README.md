# Rekordbox Now Playing Broadcaster

A Windows system-tray app that watches a running Rekordbox instance and reports the currently playing track to a now-playing API, for showing a "now playing" banner elsewhere (e.g. a song-request site).

## For end users

Download the companion app from your dashboard's "Download companion app" button, unzip it, and run `RekordboxNowPlaying.exe` from inside the extracted folder - no command line, no setup. On launch you'll get a brief popup confirming it's running, then it sits in the system tray. Right-click the tray icon for status, a "Broadcasting enabled" toggle, "Start with Windows", and "View log".

The download is a zip containing this exe plus a `config.json` with your own API token already filled in - the exe reads that file from its own folder at startup, so it's already pointed at your event with no typing required. If the tray icon shows purple ("Not set up"), `config.json` is missing or wasn't extracted alongside the exe - redownload it from the dashboard.

## How it works

- Reads the currently loaded track (title/artist) and elapsed time off Rekordbox's deck displays using Microsoft UI Automation (Rekordbox exposes this via its JUCE accessibility bridge - see `dev_tools/` for the diagnostic scripts used to reverse-engineer the UI layout).
- Play/pause is inferred from whether the elapsed timecode is actually ticking forward by a plausible amount, not just "changed" - this avoids false positives from loading a new track, seeking, or hitting a hot cue.
- When two decks are both playing (a mix transition), the reported track stays "sticky" on whichever one is currently reported until it actually stops - it only switches once the outgoing track has fully stopped, not the instant the next one starts.
- Reports are POSTed to the configured API on track change, roughly every 15s as a heartbeat while a track keeps playing, and once immediately when playback stops.

## Project layout

- `app/` - the application (scraper, state machine, API client, tray UI, splash screen)
- `main.py` - entry point
- `dev_tools/` - one-off diagnostic scripts used to map Rekordbox's UI Automation tree (not needed to run the app)
- `build.ps1` - builds a standalone `dist/RekordboxNowPlaying.exe` via PyInstaller

## Building from source

```powershell
python -m venv venv
venv\Scripts\pip install -r requirements.txt
.\build.ps1
```

Produces `dist\RekordboxNowPlaying.exe`, a standalone executable (no Python install required to run it).

## Configuration

Timing constants live in `app/config.py`. The API endpoint and auth token are no longer hardcoded there - they're read from a `config.json` file placed next to the exe at runtime (`{"apiUrl": "...", "token": "..."}`), which is how RequestApp's dashboard delivers a per-DJ token with zero manual setup: its "Download companion app" button zips this exe together with a freshly generated `config.json`. Without a `config.json` present, `config.py` falls back to a blank token (the tray shows "Not set up") - useful for local development, not for a real deploy.

## CI

`.github/workflows/build-release.yml` builds a fresh exe on `windows-latest` and publishes it as the `latest` GitHub Release on every push to `main`. RequestApp's dashboard always downloads that release's asset, so this exe never needs manual rebuilding or re-uploading - only pushing a change here.
