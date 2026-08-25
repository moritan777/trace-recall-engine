# Recall Composition Stress Dataset

`scenarios.jsonl` contains 30 deterministic, artificial associative-recall
composition scenarios. No row requires Stable Fact fidelity. Every row records
one expected target, `SHOULD_RECALL` or `SHOULD_NOT_RECALL`, responsibility,
internal recall expectation, external mention expectation, coverage tags, the
candidate ThreadGroups, and the unchanged group limit.

Run:

```bash
python src/threaded_concept_memory_probe.py composition-stress-eval \
  --output-json /tmp/composition-stress.json \
  --report-md /tmp/composition-stress.md
```

The evaluator applies the existing offline `BASELINE`, `DIRECT_MATCH_CAP`,
`GROUP_DIVERSITY`, and `GENERIC_WORD_DOWNWEIGHT` strategies to every row. It
reports recovery, leakage, explicitly annotated unexpected recall, group
inclusion, pre-fatigue admission, final Working-Memory recall, selected groups,
Working-Memory size, and counterexamples. Trade-offs are reported relative to
baseline, including leakage, unexpected recall, excessive Working-Memory growth,
and counterexample increases; recovery alone is not an acceptance criterion.

Only three of 30 rows carry `legacy_turn_11_or_97_shape`; 90% exercise a
different composition. `selected-group-but-word-suppressed` uses separate
pre-fatigue and Working-Memory word lists so governance suppression is not
misclassified as group-selection failure.

This dataset and evaluator are offline only. They do not modify Runtime
thresholds, fatigue, reinforcement, Connection Weight, group selection, or
production recall, and no strategy is connected to production.

The one recommended next step is: **baselineを維持する**. The stress results
should remain comparative evidence until a strategy improves recovery without
the reported leakage, unexpected-recall, memory-growth, or counterexample
trade-offs.

The Markdown summary classifies every strategy as `KEEP_BASELINE`,
`RESEARCH_CANDIDATE`, or `REJECT`, then audits only scenarios changed from
baseline with coverage, rank band, competition shape, both outcomes, and an
improvement/regression assessment. It separately extracts recovery that breaks
another scenario, leakage increases, unexpected-recall increases, and
Working-Memory-only growth. These classifications do not adopt a strategy.
