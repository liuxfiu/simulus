# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Simulus is a Python discrete-event simulation (DES) framework implementing both direct event scheduling and process-oriented simulation. It supports parallel/distributed simulation via multiprocessing (SMP) and MPI (SPMD).

## Commands

```bash
# Run tests
pytest -s

# Run a single test file
pytest -s tests/regress.py

# Multi-version testing
tox

# Build documentation
cd docs && make html
```

## Architecture

The simulator has two scheduling paradigms:
- **Direct event scheduling**: `sim.sched(handler, offset=t)` — schedules a function to be called at a future time
- **Process scheduling**: `sim.process(func)` — runs a function as a greenlet-based process that can `sim.sleep(t)` to suspend

### Core Components

**`simulus/simulator.py`** — Main engine. Manages the event priority queue (binary heap), greenlet context switching for processes, and the ready queue. All simulation time advances through this file's event loop.

**`simulus/simulus.py`** — Global singleton (`_Simulus`) managing all simulator instances, MPI rank state, and named random streams.

**`simulus/event.py`** — Event types (`_DirectEvent`, `_ProcessEvent`) and the `_PQDict_` priority queue. Events are keyed by `(time, serial)` tuples.

**`simulus/process.py`** — `_Process` wraps a greenlet. States: STARTED → RUNNING ↔ SUSPENDED → TERMINATED. Processes block by waiting on traps.

### Synchronization Primitives

All primitives are built on traps and semaphores:

| Class | File | Purpose |
|-------|------|---------|
| `Trap` | `trap.py` | One-shot multicast signal (UNSET → SET → SPRUNG) |
| `Semaphore` | `semaphore.py` | Counting semaphore; supports FIFO/LIFO/SIRO/PRIORITY queuing |
| `Resource` | `resource.py` | Single/multi-server facility built on semaphore |
| `Store` | `store.py` | Bounded buffer for countable objects (producer/consumer) |
| `Bucket` | `bucket.py` | Bounded buffer for continuous quantities (float amounts) |
| `Mailbox` | `mailbox.py` | Multi-partition message passing with optional time delay |

### Parallel Simulation

**`simulus/sync.py`** — Coordinates multiple `simulator` instances. In SMP mode, uses `multiprocessing`; in SPMD mode, uses `mpi4py`. Synchronization uses lookahead-based conservative algorithms to preserve causality.

### Statistics

**`simulus/utils.py`** — `DataCollector`, `TimeSeries`, `DataSeries`, `WelfordStats` (one-pass Welford algorithm). Most simulation objects (resource, store, bucket) embed a `DataCollector`.

## Key Conventions

- Queuing discipline is specified via `QDIS` constants: `QDIS.FIFO`, `QDIS.LIFO`, `QDIS.SIRO`, `QDIS.PRIORITY`
- `sim.now` gives current simulation time; `simulus.infinite_time` is used for no-timeout waits
- Processes communicate by waiting on `Trap`/`Semaphore` objects; direct event handlers cannot block
- `Store` is for discrete objects/counts; `Bucket` is for continuous quantities (e.g., fuel, water)
- MPI support requires `mpi4py`; it is optional and only used in SPMD parallel mode
