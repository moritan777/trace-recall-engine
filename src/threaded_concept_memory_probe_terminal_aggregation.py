#!/usr/bin/env python3
"""Opt-in runner for the terminal aggregation Production-compatible prototype.

Default Production entrypoint is untouched.  Use this runner only when explicitly
benchmarking the prototype.  All original CLI arguments are forwarded unchanged.
"""
from __future__ import annotations

import atexit

import threaded_concept_memory_probe as probe
from trace_recall.terminal_aggregation_runtime import TerminalAggregationActivationEngine


probe.ActivationEngine = TerminalAggregationActivationEngine


def _print_terminal_aggregation_summary() -> None:
    stats = TerminalAggregationActivationEngine.cumulative_stats
    if stats.activation_calls <= 0:
        return
    print("\n[Terminal Aggregation Prototype]")
    print("enabled: True")
    print(f"activation_calls: {stats.activation_calls}")
    print(f"physical_terminal_paths: {stats.physical_terminal_paths}")
    print(f"distinct_terminal_edges: {stats.distinct_terminal_edges}")
    print(f"operations_saved: {stats.operations_saved}")
    print(f"aggregation_ratio: {stats.aggregation_ratio:.6f}")
    print(f"activation_elapsed_ms_total: {stats.aggregation_ms:.3f}")


atexit.register(_print_terminal_aggregation_summary)


if __name__ == "__main__":
    raise SystemExit(probe.main())
