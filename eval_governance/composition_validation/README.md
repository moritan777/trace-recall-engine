# Out-of-Sample Composition Validation

`scenarios.jsonl` contains 48 independent, deterministic validation fixtures.
The existing 30 exploration scenarios remain unchanged. Validation covers eight
shapes in equal proportions: low-generic/high-overlap,
high-generic/low-overlap, high/low source diversity, flat/sharp scores,
near-duplicate groups, and almost-disjoint groups. Candidate counts range from
6 to 14 and group boundaries from 3 to 5.

Target placement is produced by a deterministic sequence independent of shape
generation. Dataset construction does not inspect the Phase 2.9 threshold or
evaluate target recovery. IDs and exact word/thread group signatures are
disjoint from exploration fixtures.

Run:

```bash
python src/threaded_concept_memory_probe.py composition-validation \
  --output-json /tmp/composition-validation.json \
  --report-md /tmp/composition-validation.md
```

The primary section applies the frozen rule
`generic_ratio >= 0.13636363636363635` without scanning or retraining. A fresh
validation-only threshold scan is reported separately as exploratory and is not
used for generalization or production judgement. Rank and coverage remain
explanation-only. No strategy, conditional switch, or production recall policy
is implemented.
