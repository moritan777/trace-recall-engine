# AIKanojyo Trace Memory Integration Package

Self-contained package for AIKanojyo developers, AIKanojyo-side Codex, future maintainers, and Shadow Mode implementers.

## What this package enables
- Understand Trace Memory goals without reading the source repository.
- Design a parallel integration beside existing AIKanojyo Memory.
- Identify C# porting scope and SQLite migration shape.
- Implement Shadow Mode, Recall comparison, Prompt A/B preparation, and adoption review.

## Read first
1. 00_EXECUTIVE_SUMMARY.md
2. 01_ARCHITECTURE.md
3. 12_IMPLEMENTATION_ORDER.md
4. 08_PORTING_MAP_PYTHON_TO_CSHARP.md
5. 06_SHADOW_MODE_PLAN.md
6. 15_ACCEPTANCE_CRITERIA.md

## Critical warnings
- Do not delete or replace existing AIKanojyo Memory.
- Do not connect Trace output directly to production responses first.
- Start with Shadow Mode.
- Do not port Oracle/Replay or the Python CLI.
- Do not aim for perfect Japanese word segmentation.

See package_manifest.json and source_snapshots/ for machine-readable metadata and reference code.
