#!/usr/bin/env python3
"""Opt-in runner for the terminal aggregation Production-compatible prototype.

The normal Production entrypoint remains unchanged/default-OFF.  Run this file
instead of threaded_concept_memory_probe.py only for explicit prototype tests;
all original CLI arguments are forwarded unchanged.
"""
from __future__ import annotations

import atexit

import threaded_concept_memory_probe as probe
from terminal_aggregation_runtime import TerminalAggregationActivationEngine


probe.ActivationEngine = TerminalAggregationActivationEngine


def _print_terminal_aggregation_summary() -> None:
    stats = TerminalAggregationActivationEngine.cumulative_stats
    if stats.physical_terminal_paths <= 0 and stats.distinct_terminal_edges <= 0:
        return
    print("\n[Terminal Aggregation Prototype]")
    print("enabled: True")
    print(f"physical_terminal_paths: {stats.physical_terminal_paths}")
    print(f"distinct_terminal_edges: {stats.distinct_terminal_edges}")
    print(f"operations_saved: {stats.operations_saved}")
    print(f"aggregation_ratio: {stats.aggregation_ratio:.6f}")
    print(f"max_edge_multiplicity: {stats.maximum_edge_multiplicity}")
    print(f"activation_elapsed_ms_total: {stats.activation_elapsed_ms:.3f}")


atexit.register(_print_terminal_aggregation_summary)


if __name__ == "__main__":
    raise SystemExit(probe.main())
