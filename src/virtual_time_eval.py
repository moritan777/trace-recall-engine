#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""Run the existing eval command with a deterministic virtual wall clock.

This wrapper does not change production/runtime behavior.  It advances the
clock only while an ``eval`` run is executing, so time-based decay can be
exercised without waiting for real days to pass.

Example::

    python src/virtual_time_eval.py eval \
      --virtual-turns-per-day 10 \
      --conversation-file eval_conversations/long_10000t_trace_recall_stress.jsonl \
      --db reports/virtual_time_10000t.db \
      --extractor fallback \
      --no-response \
      --report-md reports/virtual_time_10000t.md \
      --events-jsonl reports/virtual_time_10000t_events.jsonl \
      --metrics-csv reports/virtual_time_10000t_metrics.csv \
      --research-log-jsonl reports/virtual_time_10000t_research.jsonl
"""

from __future__ import annotations

import argparse
import datetime as dt
import sys
from dataclasses import dataclass
from typing import Sequence

import threaded_concept_memory_probe as probe


DEFAULT_VIRTUAL_START = "2026-01-01T00:00:00"


@dataclass
class VirtualEvalClock:
    """Deterministic clock used only by the evaluation wrapper."""

    start: dt.datetime
    turns_per_day: float
    completed_turns: int = 0

    def __post_init__(self) -> None:
        if self.turns_per_day <= 0:
            raise ValueError("turns_per_day must be greater than zero")

    @property
    def now(self) -> dt.datetime:
        # Turn 1 starts at the configured origin.  After N completed turns,
        # N / turns_per_day virtual days have elapsed.
        days = self.completed_turns / self.turns_per_day
        return self.start + dt.timedelta(days=days)

    def now_iso(self) -> str:
        return self.now.isoformat(timespec="microseconds")

    def advance_turn(self) -> None:
        self.completed_turns += 1


def parse_virtual_args(argv: Sequence[str]) -> tuple[argparse.Namespace, list[str]]:
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("--virtual-turns-per-day", type=float, required=True)
    parser.add_argument("--virtual-start", default=DEFAULT_VIRTUAL_START)
    virtual, remaining = parser.parse_known_args(list(argv))

    if virtual.virtual_turns_per_day <= 0:
        parser.error("--virtual-turns-per-day must be greater than zero")

    try:
        virtual.virtual_start_dt = dt.datetime.fromisoformat(virtual.virtual_start)
    except ValueError as exc:
        parser.error(f"--virtual-start must be ISO-8601 datetime: {exc}")

    return virtual, remaining


def install_virtual_clock(clock: VirtualEvalClock) -> None:
    """Patch the probe clock and advance it once after each eval turn."""

    original_run_eval_turn = probe.run_eval_turn

    def run_eval_turn_with_virtual_time(item, args, store, extractor, engine, generator):
        try:
            return original_run_eval_turn(item, args, store, extractor, engine, generator)
        finally:
            clock.advance_turn()

    # All store/activation decay code resolves now_iso from this module at
    # runtime, so replacing the module-global function is enough to drive both
    # Word and Thread last_seen/time_decay calculations with virtual time.
    probe.now_iso = clock.now_iso
    probe.run_eval_turn = run_eval_turn_with_virtual_time


def main(argv: Sequence[str] | None = None) -> int:
    raw = list(sys.argv[1:] if argv is None else argv)

    if not raw or raw[0] != "eval":
        print(
            "usage: virtual_time_eval.py eval --virtual-turns-per-day N [normal eval options]",
            file=sys.stderr,
        )
        return 2

    # Keep the existing command name for probe.main(), but strip only the
    # wrapper-specific options before handing control back to the production
    # parser.
    virtual, remaining = parse_virtual_args(raw[1:])
    probe_argv = ["eval", *remaining]

    clock = VirtualEvalClock(
        start=virtual.virtual_start_dt,
        turns_per_day=virtual.virtual_turns_per_day,
    )
    install_virtual_clock(clock)

    print(
        "[Virtual Time Eval] "
        f"start={clock.start.isoformat()} "
        f"turns_per_day={clock.turns_per_day:g}",
        file=sys.stderr,
    )

    rc = int(probe.main(probe_argv))

    print(
        "[Virtual Time Eval] "
        f"completed_turns={clock.completed_turns} "
        f"final_time={clock.now_iso()} "
        f"elapsed_days={clock.completed_turns / clock.turns_per_day:.3f}",
        file=sys.stderr,
    )
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
