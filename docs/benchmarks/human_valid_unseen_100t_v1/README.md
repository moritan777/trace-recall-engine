# Human-Valid Unseen 100T Evaluation v1

## Purpose

This evaluation tests whether the current Trace Recall configuration generalizes to a conversation fixture that was not used while tuning the implementation.

The system configuration was frozen before the results of this fixture were inspected.

This evaluation does not measure exact RAG-style retrieval accuracy.

Trace Recall is allowed to:

- recall incomplete information;
- omit available memories;
- associate related experiences;
- reconstruct memories with appropriate uncertainty.

The primary conversational failures of interest are:

- confident false memories;
- incorrect attribution;
- clear contradiction of established conversation history.

---

## Freeze Point

The implementation was frozen at:

`48cd233 Generalize LLM extractor prompt for multilingual traces`

No Prompt, Gate, WordPolicy, or recall implementation changes were made after inspecting the results of this fixture.

The fixture itself was not modified in response to recall or response quality results.

Two mechanical format corrections were made before evaluation:

- `mode: recall` was changed to the supported `mode: ask`;
- the JSONL file was rewritten as UTF-8 without BOM.

Neither correction changed conversation content, expected words, or unexpected words.

---

## Fixture

- File: `eval_conversations/unseen_100t_mixed_recall_v1.jsonl`
- Total turns: 100
- Learn turns: 51
- Ask turns: 49
- Generated responses evaluated: 49

The fixture contains memories involving:

- people and attribution;
- preferences and dislikes;
- locations;
- past events;
- future plans;
- boundaries and negation;
- changes over time;
- similar or potentially interfering memories;
- repeated and connected experiences;
- direct and ambiguous recall questions.

This is a synthetic fixture created independently from the existing `long_100t_mixed_recall.jsonl` development fixture.

---

## Configuration

### Recall

- Extractor: LLM Extractor
- Extractor model: `local-model`
- Word policy: `identity`
- Activation Gate: baseline
- `gate-cap-after-group`: disabled
- Prompt view for response evaluation: `threadgroup-source`

### Response

- Response model: `local-model`
- Response generation: LLM
- External retrieval: none
- Response LLM calls: 49 / 49

The selected ThreadGroups expose their stored `source_text` to the response model.

The application does not generate semantic labels for subject, preference, causality, or temporal relationships. Interpretation remains the responsibility of the LLM.

---

## No-Response Recall Result

The first evaluation measured the recall pipeline without generating responses.

| Metric | Result |
|---|---:|
| Expected words | 180 |
| Expected hits | 143 |
| Expected-word coverage | 79.4% |
| Unexpected hits | 6 |
| Working Memory Recall Precision | 0.960 |
| LLM extractor successes | 49 / 49 |
| Extractor fallbacks | 0 |

This result measures the recall pipeline and Working Memory selection.

It does **not** measure conversational response quality.

---

## Human-Valid Response Result

The same frozen configuration was then evaluated with local LLM responses enabled.

49 responses were reviewed.

| Classification | Count |
|---|---:|
| Human-Valid | 48 |
| Human-Invalid | 1 |
| Undetermined | 0 |

Human-Valid rate:

**48 / 49 = 98.0%**

The row-level evaluation is stored in:

`human_valid.csv`

---

## Known Failure

### Turn 56

User question:

> お茶の好みは変わった？

Earlier conversation history established:

> 以前は緑茶ばかり飲んでいました。

and:

> 最近は焙じ茶もよく飲みます。

The recall pipeline did not provide strong gated context for the response.

The generated response added a preference for stronger aromas that had not been established in the conversation history.

Classification:

- `INVALID_FALSE_MEMORY`
- `UNSUPPORTED_ADDITION`

This failure is intentionally retained without adjusting the Gate, Prompt, fixture, or expected values after evaluation.

---

## Interpretation

The most important observation is the difference between exact expected-word recovery and final conversational validity.

Recall pipeline:

**143 / 180 = 79.4% expected-word coverage**

Final response evaluation:

**48 / 49 = 98.0% Human-Valid**

This supports the current Trace Recall evaluation principle:

> Exact retrieval of every expected word is not required for a conversational response to remain valid.

A recalled memory may be incomplete or associative while still supporting a response that does not fabricate history, misattribute a memory, or contradict established conversation facts.

The result should therefore not be described as:

> 98% recall accuracy

The correct interpretation is:

> 98.0% of the evaluated responses in this unseen synthetic 100-turn fixture were judged Human-Valid under the current evaluation criteria.

---

## Comparison with Development Fixture

The earlier development fixture produced:

| Fixture | Human-Valid | Human-Invalid | Undetermined |
|---|---:|---:|---:|
| Development 100T | 48 | 2 | 1 |
| Unseen 100T v1 | 48 | 1 | 0 |

For the development fixture, the determined Human-Valid rate was:

**48 / 50 = 96.0%**

For this unseen fixture:

**48 / 49 = 98.0%**

The unseen result does not show an obvious loss of conversational validity relative to the repeatedly inspected development fixture.

However, this is still a single synthetic unseen fixture and should not be treated as a general performance estimate.

---

## Limitations

This evaluation has several important limitations.

1. The fixture is synthetic.
2. Only one unseen 100-turn conversation was evaluated.
3. The response model is a local LLM, so output may vary between runs.
4. Human-Valid evaluation depends on the documented classification criteria.
5. Exact expected-word matching and Human-Valid response evaluation measure different properties.
6. A 98.0% result from 49 responses is not sufficient to establish general reliability across languages, conversation styles, models, or substantially longer histories.

The fixture should remain frozen now that its results have been inspected.

Future implementation tuning must not use this fixture as an unseen validation set.

---

## Next Research Step

Do not tune the current implementation against failures in this fixture.

Future validation should use another independently prepared fixture or a different evaluation domain while keeping the implementation frozen beforehand.

The current fixture may now be used for regression testing, but no longer as an unseen evaluation set.