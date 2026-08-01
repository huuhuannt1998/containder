"""Shared process-pool runner for the confirmatory feeder experiments.

OpenDSS is a single global circuit per process, so arms cannot be interleaved within one
interpreter. They are independent by construction, though -- the pre-registered protocol requires
a fresh compile per arm precisely so that no solver state carries over -- which makes them safe
to distribute across processes. Each worker owns its own OpenDSS instance and its own working
directory.

Progress is reported from the parent as tasks complete, because a child's stdout is buffered and
a long sweep that prints nothing is indistinguishable from one that has hung.
"""
from __future__ import annotations

import os
import sys
import time
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

_WORKER_STATE = {"feeder": None}


def _init_worker():
    # Children inherit the parent's cwd; each will chdir per task as feeders change.
    os.environ.setdefault("PYTHONHASHSEED", "0")


def ensure_feeder(key: str):
    """Chdir the calling worker to ``key``'s feeder directory, at most once per change."""
    from power import confirmatory as C
    if _WORKER_STATE["feeder"] != key:
        C.chdir_feeder(C.FEEDERS[key])
        _WORKER_STATE["feeder"] = key
    return C.FEEDERS[key]


def run_tasks(fn, tasks, *, workers: int = None, label: str = "", every: int = 25):
    """Map ``fn`` over ``tasks`` in a process pool, printing progress from the parent.

    ``fn`` must be a module-level function (picklable) taking one task and returning one dict.
    Results come back in completion order; every task carries its own identifying fields, so
    order is not relied upon.
    """
    workers = workers or max(1, min(8, (os.cpu_count() or 2) - 2))
    out = []
    t0 = time.time()
    n = len(tasks)
    print(f"[{label}] {n} arms on {workers} workers", flush=True)
    with ProcessPoolExecutor(max_workers=workers, initializer=_init_worker) as ex:
        futs = {ex.submit(fn, t): t for t in tasks}
        done = 0
        for f in as_completed(futs):
            try:
                out.append(f.result())
            except Exception as exc:                      # keep the sweep alive, record the loss
                t = futs[f]
                out.append({"task": t, "error": f"{type(exc).__name__}: {exc}"})
                print(f"[{label}] ARM FAILED {t}: {type(exc).__name__}: {exc}", flush=True)
            done += 1
            if done % every == 0 or done == n:
                el = time.time() - t0
                rate = done / el if el else 0
                print(f"[{label}] {done}/{n}  {el:6.1f}s elapsed  "
                      f"{(n - done) / rate if rate else 0:6.1f}s remaining", flush=True)
    return out
