APP_NAME = "Rekordbox Now Playing"

API_URL = "https://songrequester.netlify.app/api/report-now-playing"
API_TOKEN = "rekordboxconnect"

POLL_INTERVAL_SECONDS = 1.0
HEARTBEAT_INTERVAL_SECONDS = 15.0
REQUEST_TIMEOUT_SECONDS = 5.0

PAUSE_DEBOUNCE_POLLS = 2

# A same-track elapsed-time change of at most this many seconds is treated
# as normal playback ticking forward. Anything bigger (or backwards) is a
# seek/hot-cue/needle-drop jump, not proof that the deck is playing.
MAX_PLAUSIBLE_TICK_SECONDS = 2
