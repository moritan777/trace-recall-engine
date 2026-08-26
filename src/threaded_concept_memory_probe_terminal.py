#!/usr/bin/env python3
from __future__ import annotations

import threaded_concept_memory_probe as probe
from terminal_aggregation_runtime import TerminalAggregationActivationEngine


def main() -> int:
    # Opt-in prototype only. Baseline script remains unchanged.
    probe.ActivationEngine = TerminalAggregationActivationEngine
    return int(probe.main())


if __name__ == "__main__":
    raise SystemExit(main())
