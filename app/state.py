"""
State machine that turns raw deck scrapes into broadcast decisions.

Play/pause detection: a deck's elapsed timecode only has 1-second
resolution, so on any given poll it may happen to read the same value as
the previous poll even while playing. A deck is marked "playing" the
instant its timecode advances by a plausible amount, and only marked
"paused" after it has been seen unchanged for PAUSE_DEBOUNCE_POLLS
consecutive polls - this absorbs that jitter without meaningfully delaying
pause detection.

Not every change in the elapsed field means real time passed, though:

- Loading a new track onto a deck jumps its elapsed reading to a cue
  point. To avoid reporting a freshly-loaded-but-not-yet-playing track as
  playing, an elapsed change only counts as a play signal when the deck's
  title/artist stayed the same as the previous poll. A title/artist change
  is treated as a load event: tracking resets and the deck is marked
  not-playing until a later poll shows the elapsed value actually
  advancing on that same track.

- Scrubbing/seeking, a needle drop, or jumping to a hot cue also changes
  the elapsed reading on the *same* track, without the track necessarily
  playing (e.g. previewing a spot while paused, or checking a mix point
  before actually bringing the track in). These show up as a jump that
  isn't a plausible ~1-second tick (too big, or backwards). Such a jump
  only counts as a play signal if the deck was already confirmed playing
  (a DJ triggering a hot cue mid-track is a normal move and shouldn't make
  the deck look stopped); if the deck wasn't already playing, a jump alone
  doesn't confirm playback - we wait for a subsequent poll to show a
  plausible tick forward from the new position.

Now-playing deck selection is sticky: once a deck is reported as the now
playing track, it stays reported for as long as it keeps playing - even
after a second deck also starts playing (cueing up / blending in the next
track). The reported track only switches once the currently-reported deck
actually stops (the outgoing track has been fully mixed out), at which
point whichever deck is still playing becomes the new primary. This
matches how a DJ transition actually reads to an audience: the track
that's live doesn't change just because the next one has started playing
underneath it.
"""
import dataclasses
import time

from . import config


def _parse_seconds(mmss):
    minutes, seconds = mmss.split(":")
    return int(minutes) * 60 + int(seconds)


@dataclasses.dataclass
class _DeckTrack:
    last_title: str = None
    last_artist: str = None
    last_elapsed: str = None
    unchanged_count: int = 0
    is_playing: bool = False
    became_playing_at: float = 0.0


@dataclasses.dataclass
class BroadcastDecision:
    should_send: bool
    is_playing: bool
    title: str = None
    artist: str = None


class PlaybackState:
    def __init__(self):
        self._decks = {}
        self._primary_index = None
        self._last_sent_title = None
        self._last_sent_artist = None
        self._last_sent_is_playing = None
        self._last_send_time = 0.0

    def _update_deck(self, deck):
        track = self._decks.setdefault(deck.index, _DeckTrack())
        now = time.monotonic()

        if (deck.title, deck.artist) != (track.last_title, track.last_artist):
            # New track loaded onto this deck (or first time we've seen it).
            # Its elapsed field just jumped too, but that's not playback -
            # wait for a later poll to confirm it's actually advancing.
            track.last_title = deck.title
            track.last_artist = deck.artist
            track.last_elapsed = deck.elapsed
            track.unchanged_count = 0
            track.is_playing = False
            return track

        if deck.elapsed == track.last_elapsed:
            track.unchanged_count += 1
            if track.unchanged_count >= config.PAUSE_DEBOUNCE_POLLS:
                track.is_playing = False
        else:
            track.unchanged_count = 0
            delta = _parse_seconds(deck.elapsed) - _parse_seconds(track.last_elapsed)
            is_plausible_tick = 0 < delta <= config.MAX_PLAUSIBLE_TICK_SECONDS

            if is_plausible_tick or track.is_playing:
                # Either a normal forward tick, or a jump (hot cue, seek)
                # on a deck that was already confirmed playing - a jump
                # mid-playback doesn't mean playback stopped.
                if not track.is_playing:
                    track.became_playing_at = now
                track.is_playing = True
            # else: a jump on a deck that wasn't already playing (scrubbing/
            # previewing/hot-cueing while paused) - not proof of playback,
            # stay not-playing until a later poll shows a plausible tick.

        track.last_elapsed = deck.elapsed
        return track

    def _pick_primary(self, decks):
        playing = {}
        for deck in decks:
            track = self._decks.get(deck.index)
            if track and track.is_playing:
                playing[deck.index] = deck

        if not playing:
            self._primary_index = None
            return None

        # Sticky: keep reporting the deck already established as primary
        # for as long as it's still playing, even if another deck is now
        # also playing underneath it.
        if self._primary_index in playing:
            return playing[self._primary_index]

        if len(playing) == 1:
            (index, deck), = playing.items()
            self._primary_index = index
            return deck

        # No current primary is playing (first poll, or the previous
        # primary just stopped on this same poll another one started) -
        # break the tie by whichever started playing most recently.
        index, deck = max(playing.items(), key=lambda pair: self._decks[pair[0]].became_playing_at)
        self._primary_index = index
        return deck

    def evaluate(self, decks):
        """decks: list of scraper.DeckInfo for this poll. Returns a
        BroadcastDecision telling the caller whether to POST, and with
        what payload."""
        for deck in decks:
            self._update_deck(deck)

        primary = self._pick_primary(decks)
        now = time.monotonic()

        if primary is None:
            if self._last_sent_is_playing is not False:
                self._last_sent_is_playing = False
                self._last_sent_title = None
                self._last_sent_artist = None
                self._last_send_time = now
                return BroadcastDecision(should_send=True, is_playing=False)
            return BroadcastDecision(should_send=False, is_playing=False)

        track_changed = (
            primary.title != self._last_sent_title
            or primary.artist != self._last_sent_artist
            or self._last_sent_is_playing is not True
        )
        if track_changed:
            self._last_sent_title = primary.title
            self._last_sent_artist = primary.artist
            self._last_sent_is_playing = True
            self._last_send_time = now
            return BroadcastDecision(
                should_send=True, is_playing=True, title=primary.title, artist=primary.artist
            )

        if now - self._last_send_time >= config.HEARTBEAT_INTERVAL_SECONDS:
            self._last_send_time = now
            return BroadcastDecision(
                should_send=True, is_playing=True, title=primary.title, artist=primary.artist
            )

        return BroadcastDecision(should_send=False, is_playing=True)

    def current_display(self):
        """Best-known (title, artist) for UI display, even on polls where
        nothing new was sent to the server."""
        return self._last_sent_title, self._last_sent_artist
