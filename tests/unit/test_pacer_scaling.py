"""Bound queue work and retain arbitrary cancellation semantics."""

from swgoh_comlink import retry


class CountedInterval(float):
    additions = 0

    def __radd__(self, other):
        type(self).additions += 1
        return other + float(self)


def test_large_pending_queue_requires_linear_deadline_work(monkeypatch):
    monkeypatch.setattr(retry, "_clock", lambda: 0.0)
    CountedInterval.additions = 0
    pacer = retry._Pacer(CountedInterval(1), frozenset())
    count = 10_000
    slots = [pacer.reserve_slot("key", "endpoint") for _ in range(count)]
    assert slots[-1][0] == count - 1
    # Two deadline operations per insertion, independent of queue length.
    assert CountedInterval.additions <= 2 * count
    for _, release in slots[::2]:
        release()
    for _, release in reversed(slots[1::2]):
        release()
    assert pacer.reserve("key", "endpoint") == 0


def test_repeated_release_cannot_cancel_reused_deadline(monkeypatch):
    monkeypatch.setattr(retry, "_clock", lambda: 0.0)
    pacer = retry._Pacer(1, frozenset())
    _, release = pacer.reserve_slot("key", "endpoint")
    release()
    assert pacer.reserve("key", "endpoint") == 0
    release()
    assert pacer.reserve("key", "endpoint") == 1
