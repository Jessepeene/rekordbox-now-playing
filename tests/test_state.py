"""
Tests for the play/pause/transition state machine in app/state.py.

No UI Automation involved: each poll is a list of synthetic deck snapshots
fed straight into PlaybackState.evaluate(), and time.monotonic() is
replaced with a fake clock that advances one poll interval per poll.
"""
import dataclasses

import pytest

from app import config, state


@dataclasses.dataclass
class Deck:
    """Same shape as scraper.DeckInfo, without importing uiautomation."""
    index: int
    title: str
    artist: str
    elapsed: str


def mmss(seconds):
    return f"{seconds // 60}:{seconds % 60:02d}"


class FakeClock:
    def __init__(self, start=1000.0):
        self.now = start

    def __call__(self):
        return self.now


class Session:
    """Drives a PlaybackState one poll at a time."""

    def __init__(self, clock):
        self.clock = clock
        self.state = state.PlaybackState()

    def poll(self, *decks, dt=config.POLL_INTERVAL_SECONDS):
        self.clock.now += dt
        return self.state.evaluate(list(decks))


@pytest.fixture
def clock(monkeypatch):
    fake = FakeClock()
    monkeypatch.setattr(state.time, "monotonic", fake)
    return fake


@pytest.fixture
def session(clock):
    return Session(clock)


def a(seconds):
    return Deck(1, "Track A", "Artist A", mmss(seconds))


def b(seconds):
    return Deck(2, "Track B", "Artist B", mmss(seconds))


def start_playing(session, deck_at, start=60, other=()):
    """Load a track at `start` and tick it forward once, so it's confirmed
    playing. Returns the next elapsed second."""
    session.poll(deck_at(start), *other)
    session.poll(deck_at(start + 1), *other)
    return start + 2


# 1. Normal playback

def test_first_poll_with_nothing_playing_reports_stopped_once(session):
    # The state starts out "unknown", so the first quiet poll clears
    # whatever the server last heard.
    assert session.poll(a(60)) == state.BroadcastDecision(should_send=True, is_playing=False)
    assert session.poll(a(60)) == state.BroadcastDecision(should_send=False, is_playing=False)


def test_freshly_loaded_track_is_not_playing_until_it_ticks(session):
    first = session.poll(a(60))
    assert not first.is_playing

    decision = session.poll(a(61))
    assert decision == state.BroadcastDecision(
        should_send=True, is_playing=True, title="Track A", artist="Artist A"
    )


def test_steady_playback_reports_once_then_stays_quiet(session):
    t = start_playing(session, a)
    for _ in range(5):
        decision = session.poll(a(t))
        assert decision.is_playing
        assert not decision.should_send
        t += 1


def test_track_change_on_same_deck_is_reported(session):
    t = start_playing(session, a)
    session.poll(a(t))

    # Loading a new track is not playback by itself...
    new_track = Deck(1, "Track C", "Artist C", "0:00")
    load = session.poll(new_track)
    assert load == state.BroadcastDecision(should_send=True, is_playing=False)

    # ...but once it ticks, it is reported.
    decision = session.poll(dataclasses.replace(new_track, elapsed="0:01"))
    assert decision.should_send and decision.is_playing
    assert (decision.title, decision.artist) == ("Track C", "Artist C")


def test_largest_plausible_tick_counts_as_playing(session):
    session.poll(a(60))
    decision = session.poll(a(60 + config.MAX_PLAUSIBLE_TICK_SECONDS))
    assert decision.is_playing


# 2. Seek / hot cue / needle drop

@pytest.mark.parametrize(
    "jump_to",
    [60 + config.MAX_PLAUSIBLE_TICK_SECONDS + 1, 150, 30],
    ids=["just-too-big", "forward-jump", "backwards"],
)
def test_jump_on_a_stopped_deck_is_not_proof_of_playing(session, jump_to):
    session.poll(a(60))
    decision = session.poll(a(jump_to))
    assert not decision.is_playing
    assert not decision.should_send

    # A plausible tick from the new position does confirm playback.
    decision = session.poll(a(jump_to + 1))
    assert decision.is_playing and decision.should_send


@pytest.mark.parametrize("jump_to", [200, 10], ids=["forward-jump", "backwards"])
def test_jump_on_a_playing_deck_keeps_it_playing(session, jump_to):
    t = start_playing(session, a)
    session.poll(a(t))

    decision = session.poll(a(jump_to))
    assert decision.is_playing
    assert not decision.should_send  # same track, nothing new to report

    assert session.poll(a(jump_to + 1)).is_playing


# 3. Pause debounce

def test_pause_is_only_detected_after_debounce_polls(session):
    t = start_playing(session, a)
    paused_at = a(t)
    session.poll(paused_at)  # last advancing poll

    for _ in range(config.PAUSE_DEBOUNCE_POLLS - 1):
        decision = session.poll(paused_at)
        assert decision.is_playing, "one repeated reading is normal 1s-resolution jitter"
        assert not decision.should_send

    decision = session.poll(paused_at)
    assert decision == state.BroadcastDecision(should_send=True, is_playing=False)


def test_single_repeated_reading_does_not_interrupt_playback(session):
    t = start_playing(session, a)
    session.poll(a(t))
    session.poll(a(t))  # timecode happened to read the same value twice
    decision = session.poll(a(t + 1))
    assert decision.is_playing
    assert not decision.should_send


def test_resume_after_pause_is_reported(session):
    t = start_playing(session, a)
    for _ in range(config.PAUSE_DEBOUNCE_POLLS + 1):
        session.poll(a(t))
    decision = session.poll(a(t + 1))
    assert decision.should_send and decision.is_playing
    assert decision.title == "Track A"


# 4. Two-deck transition

def test_reported_deck_is_sticky_until_outgoing_track_stops(session):
    t_a = start_playing(session, a, other=[b(0)])
    t_b = 1

    # Deck B starts playing underneath A: still reporting A.
    for _ in range(5):
        decision = session.poll(a(t_a), b(t_b))
        assert decision.is_playing
        assert not decision.should_send
        assert session.state.current_display() == ("Track A", "Artist A")
        t_a += 1
        t_b += 1

    # A stops (deck paused at its last reading). Until the debounce
    # expires it still counts as playing, so nothing changes yet.
    stopped_a = a(t_a - 1)
    for _ in range(config.PAUSE_DEBOUNCE_POLLS - 1):
        decision = session.poll(stopped_a, b(t_b))
        t_b += 1
        assert not decision.should_send
        assert session.state.current_display() == ("Track A", "Artist A")

    # Then the report switches straight to B, without a "stopped" in between.
    decision = session.poll(stopped_a, b(t_b))
    t_b += 1
    assert decision == state.BroadcastDecision(
        should_send=True, is_playing=True, title="Track B", artist="Artist B"
    )
    assert not session.poll(stopped_a, b(t_b)).should_send


def test_outgoing_track_unloaded_switches_to_the_other_playing_deck(session):
    t_a = start_playing(session, a, other=[b(0)])
    session.poll(a(t_a), b(1))
    session.poll(a(t_a + 1), b(2))

    # Loading a new track onto deck A makes it not-playing immediately.
    decision = session.poll(Deck(1, "Track C", "Artist C", "0:00"), b(3))
    assert decision.should_send
    assert decision.title == "Track B"


# 5. Heartbeat

def test_same_track_is_re_reported_after_heartbeat_interval(session, clock):
    t = start_playing(session, a)
    last_report = clock.now

    while clock.now + config.POLL_INTERVAL_SECONDS - last_report < config.HEARTBEAT_INTERVAL_SECONDS:
        assert not session.poll(a(t)).should_send
        t += 1

    decision = session.poll(a(t))
    assert decision == state.BroadcastDecision(
        should_send=True, is_playing=True, title="Track A", artist="Artist A"
    )
    assert clock.now - last_report == pytest.approx(config.HEARTBEAT_INTERVAL_SECONDS)

    # The heartbeat restarts the interval.
    assert not session.poll(a(t + 1)).should_send


def test_track_change_resets_heartbeat_interval(session, clock):
    t = start_playing(session, a, other=[b(0)])
    session.poll(a(t), b(0), dt=config.HEARTBEAT_INTERVAL_SECONDS - 1)

    # Deck A gets unloaded right before its heartbeat is due; B is
    # reported instead, which counts as the latest send.
    decision = session.poll(Deck(1, "Track C", "Artist C", "0:00"), b(1))
    assert decision.title == "Track B" and decision.should_send

    # A's heartbeat would have been due now, but B was just sent.
    assert not session.poll(Deck(1, "Track C", "Artist C", "0:00"), b(2)).should_send


def test_no_heartbeat_while_stopped(session, clock):
    session.poll(a(60))  # initial stopped report
    decision = session.poll(a(60), dt=config.HEARTBEAT_INTERVAL_SECONDS * 4)
    assert not decision.should_send


# 6. Both decks stopped

def test_both_decks_stopping_reports_stop_exactly_once(session):
    t_a = start_playing(session, a, other=[b(0)])
    t_b = 1
    for _ in range(3):
        session.poll(a(t_a), b(t_b))
        t_a += 1
        t_b += 1

    # Both decks freeze at their last reading.
    decisions = [session.poll(a(t_a - 1), b(t_b - 1)) for _ in range(10)]

    stops = [d for d in decisions if d.should_send]
    assert stops == [state.BroadcastDecision(should_send=True, is_playing=False)]
    assert all(not d.is_playing for d in decisions[config.PAUSE_DEBOUNCE_POLLS - 1:])


def test_no_decks_visible_reports_stop_once(session):
    t = start_playing(session, a)
    session.poll(a(t))
    assert session.poll() == state.BroadcastDecision(should_send=True, is_playing=False)
    assert session.poll() == state.BroadcastDecision(should_send=False, is_playing=False)
