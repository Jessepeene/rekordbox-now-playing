# Rekordbox Now Playing Broadcaster

A Windows system-tray app that watches a running Rekordbox instance and reports the currently playing track to a now-playing API, for showing a "now playing" banner elsewhere (e.g. a song-request site).

## For end users

Download the app (a zip) and your `config.json` from your dashboard's "Your guest page" section (two separate downloads), unzip the app, put `config.json` inside that same unzipped folder next to `RekordboxNowPlaying.exe`, and run the exe - no command line, no setup. On launch it sits in the system tray and shows a brief tray notification confirming it's running. Right-click the tray icon for status, a "Broadcasting enabled" toggle, "Start with Windows", and "View log".

The exe reads `config.json` from its own folder at startup, so it's already pointed at your event with no typing required, as long as both files are in the same folder. If the tray icon shows purple ("Not set up"), `config.json` is missing from that folder - redownload it from the dashboard.

Windows or your antivirus may flag the download as suspicious the first time - that's a false positive common to small, unsigned, freshly-built executables (especially ones using UI Automation, which legitimate tools and spyware both use to read text from other windows). Click "More info" -> "Run anyway" if you see a SmartScreen prompt.

## How it works

- Reads the currently loaded track (title/artist) and elapsed time off Rekordbox's deck displays using Microsoft UI Automation (Rekordbox exposes this via its JUCE accessibility bridge - see `dev_tools/` for the diagnostic scripts used to reverse-engineer the UI layout).
- Play/pause is inferred from whether the elapsed timecode is actually ticking forward by a plausible amount, not just "changed" - this avoids false positives from loading a new track, seeking, or hitting a hot cue.
- When two decks are both playing (a mix transition), the reported track stays "sticky" on whichever one is currently reported until it actually stops - it only switches once the outgoing track has fully stopped, not the instant the next one starts.
- Reports are POSTed to the configured API on track change, roughly every 15s as a heartbeat while a track keeps playing, and once immediately when playback stops.

## Project layout

- `app/` - the application (scraper, state machine, API client, tray UI)
- `main.py` - entry point
- `dev_tools/` - one-off diagnostic scripts used to map Rekordbox's UI Automation tree (not needed to run the app)
- `build.ps1` - builds `dist/RekordboxNowPlaying/` via PyInstaller and zips it to `dist/RekordboxNowPlaying.zip`

## Building from source

```powershell
python -m venv venv
venv\Scripts\pip install -r requirements.txt
.\build.ps1
```

Produces `dist\RekordboxNowPlaying.zip` (containing `RekordboxNowPlaying.exe` plus its supporting files - no Python install required to run it). Built with PyInstaller's default `--onedir` mode rather than `--onefile`: onefile's runtime self-extraction into a temp directory is exactly the behavior pattern antivirus heuristics associate with malware droppers, so unpacking everything at build time instead (into a zip) measurably reduces false-positive detections for an unsigned exe like this one.

## Configuration

Timing constants live in `app/config.py`. The API endpoint and auth token are no longer hardcoded there - they're read from a `config.json` file placed next to the exe at runtime (`{"apiUrl": "...", "token": "..."}`), which is how RequestApp's dashboard delivers a per-DJ token with zero manual setup: it links directly to this repo's released zip, and a separate small dashboard endpoint hands back a freshly generated `config.json` to place alongside it. Without a `config.json` present, `config.py` falls back to a blank token (the tray shows "Not set up") - useful for local development, not for a real deploy.

## CI

`.github/workflows/build-release.yml` builds a fresh zip on `windows-latest` and publishes it as the `latest` GitHub Release on every push to `main`. RequestApp's dashboard always links to that release's asset, so this never needs manual rebuilding or re-uploading - only pushing a change here.
