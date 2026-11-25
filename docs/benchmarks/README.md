## Trace Recall Engine Benchmarks

This directory contains public benchmark and evaluation reports for the Trace Recall Engine.

The benchmark suite has two complementary purposes:

1. evaluate whether trace-based recall can scale while keeping Working Memory and prompt size bounded;
2. evaluate whether recalled traces can support human-valid conversational responses without turning Trace Recall into an exact RAG-style retrieval system.

### Scope

The scale benchmarks primarily evaluate recall behavior, Working Memory size, prompt size, and scalability.

Human-Valid evaluations examine final conversational responses separately. They allow incomplete, associative, and uncertain reconstruction, while treating confident false memories, incorrect attribution, and clear contradiction of established history as failures.

These evaluations do not establish superiority over other memory systems.

CSV, JSONL, SQLite databases, and sensitivity outputs are local generated artifacts unless explicitly committed.

### Benchmark Index

<table>
<tr>
<th>ID</th>
<th>Scenario</th>
<th>Mode</th>
<th>Report</th>
</tr>

<tr>
<td>001</td>
<td>100T Weighted vs Count</td>
<td>response enabled</td>
<td>[100T summary](0001_100T.md), [Weighted](0001_long100_weighted.md), [Count](0001_long100_count.md)</td>
</tr>

<tr>
<td>002</td>
<td>1000T Count</td>
<td>no-response</td>
<td>[1000T summary](0002_1000T.md), [Count details](0002_long1000_count.md)</td>
</tr>

<tr>
<td>003</td>
<td>3000T Count</td>
<td>no-response</td>
<td>[3000T summary](0003_3000T.md), [Count details](0003_long3000_count.md)</td>
</tr>

<tr>
<td>004</td>
<td>10000T Count</td>
<td>no-response</td>
<td>[10000T summary](0004_10000T.md), [Count details](0004_long10000_count.md)</td>
</tr>
</table>

### Human-Valid Response Evaluation

Human-Valid evaluation is intentionally separate from exact recall scoring.

Trace Recall is allowed to behave like imperfect memory:

- recall may be incomplete;
- related experiences may be associated;
- uncertain reconstruction is allowed;
- an available memory does not have to be mentioned.

The primary conversational failures of interest are:

- confident fabrication of past events;
- incorrect attribution to a person;
- clear contradiction of established conversation history.

#### 100T Development Fixture

- [Human-Valid 100T source-text evaluation](human_valid_100t_source_local/README.md)
- Configuration: LLM Extractor + baseline Activation Gate + `threadgroup-source` + local response model
- Evaluated responses: 51
- Human-Valid: 48
- Human-Invalid: 2
- Undetermined: 1
- Determined Human-Valid rate: 48 / 50 = 96.0%

This result is from a **development fixture**, not an unseen benchmark.

`long_100t_mixed_recall.jsonl` was repeatedly inspected during development, and the Human-Valid criterion was refined during the same research process. The 96.0% result must therefore not be interpreted as general recall accuracy or unseen benchmark performance.

The next Human-Valid evaluation should use a frozen configuration on an unseen conversation fixture.

### Four-Stage Research Story

<table>
<tr>
<th>Scale</th>
<th>Research Question</th>
<th>Main Result</th>
</tr>

<tr>
<td>100T</td>
<td>Weighted or Count?</td>
<td>Count was selected as the current Baseline.</td>
</tr>

<tr>
<td>1,000T</td>
<td>Does Count remain usable at longer scale?</td>
<td>Long-term Count behavior remained usable in the public stress scenario.</td>
</tr>

<tr>
<td>3,000T</td>
<td>Does the pipeline scale further?</td>
<td>Working Memory and prompt size remained bounded in the stress scenario.</td>
</tr>

<tr>
<td>10,000T</td>
<td>Does practical-scale use collapse?</td>
<td>Prompt size did not grow with total history; the 10,000T no-response summary reports a Working Memory precision-like value of 0.927 (not final response precision), average prompt size 429 tokens, average ThreadGroups 1.78, and 764 fatigue suppressions.</td>
</tr>
</table>

### Key Findings

- Count-based Thread accumulation was adopted over Weighted Thread Strength for the current Baseline.
- ThreadGroup compression prevents repeated experiences from expanding prompts directly.
- Activation Gate separates broad Raw Activation from bounded Working Memory selection.
- Conversation Fatigue separates recall strength from repeated prompt exposure.
- 10000T evaluation confirmed that prompt size scales with Working Memory size, not with total conversation length, in the public stress scenario.
- Human-Valid evaluation is treated separately from exact recall accuracy.
- Supplying verbatim `source_text` for already-selected ThreadGroups is being evaluated as a way to preserve linguistic relations without adding application-side semantic labels.
- In the current development fixture, LLM Extractor + baseline Gate + `threadgroup-source` + local response model produced 48 Human-Valid responses, 2 Human-Invalid responses, and 1 Undetermined response across 51 evaluated responses.
- The current 100T Human-Valid result is a development-set result and requires validation on an unseen fixture before broader claims are made.

### Interpretation

The benchmark history should be read as evidence that the primary researchand toward selection, extraction boundaries, and how incomplete recalled traces are reconstructed into conversation.

The Human-Valid evaluation extends this question beyond recall hit rates. Trace Recall is not intended to reproduce stored history with database-like precision. The research question is whether incomplete and associative recall can still produce conversationally valid behavior without introducing unacceptable false memories, attribution errors, or contradictions.

### Next Benchmark Phase

The immediate next Human-Valid benchmark should use an unseen conversation fixture with the current configuration frozen before results are inspected.

The existing 100T conversation remains a development fixture for diagnosis and regression testing.

See also:

- [Current Research Direction](../research/current_research_direction.md)
- [Extractor Research Plan](../research/extractor_research_plan.md)

### Related History

- [Benchmark History](benchmark_history.md)
- [Research Log](Research_Log.md)

Benchmarks explain what happened.

For why the architecture was designed this way:
→ Architecture

For development history:
→ note
