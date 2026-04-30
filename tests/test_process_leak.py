"""Regression test for issue #22: _Process / greenlet leak."""

import gc

import simulus
from simulus.process import _Process


def _live_processes_for(sim):
    return [o for o in gc.get_objects()
            if isinstance(o, _Process) and o._sim is sim]


def test_process_releases_after_natural_exit():
    sim = simulus.simulator()

    def f():
        sim.sleep(1)

    procs = [sim.process(f) for _ in range(10)]
    sim.run()
    assert sim.now == 1

    for p in procs:
        assert p.vert.dead, "greenlet not dead after natural exit"

    del procs, p
    gc.collect()
    assert _live_processes_for(sim) == [], \
        "leaked _Process bound to this simulator after natural exit"


def test_process_releases_after_external_kill():
    sim = simulus.simulator()

    def f():
        sim.sleep(1000)  # long sleep — kill before it wakes

    procs = [sim.process(f) for _ in range(10)]
    # advance into the processes so each greenlet is started and
    # suspended, not still in STATE_STARTED
    sim.run(until=0.5)
    for p in procs:
        sim.kill(p)
    sim.run(until=2000)  # drain anything else

    for p in procs:
        assert p.vert.dead, "greenlet not dead after external kill"

    del procs, p
    gc.collect()
    assert _live_processes_for(sim) == [], \
        "leaked _Process bound to this simulator after external kill"
