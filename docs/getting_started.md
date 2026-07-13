# Getting Started

This guide explains how to run **Trace Recall Engine** in a new environment.

The current implementation is a research prototype optimized for Japanese conversations. It uses only Python's standard library, but LLM-backed trace extraction and response generation require an OpenAI-compatible local or remote API.

---

## 1. Requirements

- Python 3.10 or later
- Git
- Optional: an OpenAI-compatible LLM endpoint

Check Python:

```bash
python --version
```

No `pip install` step is required for the current prototype. Python 3.10 compatibility was verified with the standard-library `unittest` suite; the default development environment may use a newer Python.

---

## 2. Clone the Repository

```bash
git clone https://github.com/moritan777/trace-recall-engine.git
cd trace-recall-engine
```

Create a directory for local databases and reports:

### Windows Command Prompt

```bat
if not exist reports mkdir reports
```

### Linux / macOS

```bash
mkdir -p reports
```

The `reports/` directory is ignored by Git and is intended for local output.

---

## 3. Command Structure

The main entry point is:

```bash
python src/threaded_concept_memory_probe.py [global options] <command> [command options]
```

Main commands include:

- `add` — extract traces from one utterance and store them
- `ask` — recall traces for one input and optionally generate a response
- `chat` — run an interactive conversation
- `prompt-preview` — inspect activation, recall selection, Working Memory, and the generated prompt
- `eval` — run a JSONL evaluation scenario
- `threads` — inspect stored threads
- `words` — inspect stored word nodes
- `seed-tests` — run built-in seed-oriented checks
- `bootstrap-identity` — store initial user and assistant recognition traces
- `config` — inspect effective configuration

To view all options:

```bash
python src/threaded_concept_memory_probe.py --help
```

To view options for a command:

```bash
python src/threaded_concept_memory_probe.py eval --help
```

---

## 4. First Run Without an LLM

The probe can run without an LLM by using its local fallback extraction path.

This is useful for checking the database, activation flow, and CLI operation. It is not expected to match the quality of the LLM extractor.

### Add one utterance

```bash
python src/threaded_concept_memory_probe.py \
  --db reports/quickstart.db \
  add "僕はチーズケーキが好きです。"
```

### Preview recall

```bash
python src/threaded_concept_memory_probe.py \
  --db reports/quickstart.db \
  prompt-preview "僕は何が好き？" \
  --show-prompt
```

On Windows Command Prompt:

```bat
python src/threaded_concept_memory_probe.py ^
  --db reports/quickstart.db ^
  add "僕はチーズケーキが好きです。"

python src/threaded_concept_memory_probe.py ^
  --db reports/quickstart.db ^
  prompt-preview "僕は何が好き？" ^
  --show-prompt
```

The output shows:

```text
Raw Activation
↓
Activation Trace
↓
Recall Selection
↓
Conversation Fatigue
↓
Working Memory Candidate
↓
Prompt
```

---

## 5. Current Extraction Status

The current research Baseline uses the LLM Extractor when an endpoint is configured through `--base-url`.

Without an endpoint, the probe uses an Implemented fallback extraction path. The fallback path is intended for diagnostics and basic operation; it is not yet the selected production Extractor.

A deterministic local Extractor is the next major research target. The CLI now exposes `--extractor` with `llm` (default) and `fallback` so the existing implementations can be selected through the same boundary; `local-rule`, Sudachi, and MeCab extractors are not implemented yet.

---

## 6. Run With an OpenAI-Compatible LLM

For the intended research path, connect an OpenAI-compatible chat endpoint.

Example local endpoint:

```text
http://127.0.0.1:8080
```

Example model alias:

```text
local-model
```

### Add a trace using the LLM extractor

```bash
python src/threaded_concept_memory_probe.py \
  --db reports/quickstart_llm.db \
  --base-url http://127.0.0.1:8080 \
  --model local-model \
  add "僕はチーズケーキが好きです。"
```

Windows Command Prompt:

```bat
python src/threaded_concept_memory_probe.py ^
  --db reports/quickstart_llm.db ^
  --base-url http://127.0.0.1:8080 ^
  --model local-model ^
  add "僕はチーズケーキが好きです。"
```

A successful extraction prints a saved thread and its words.

Example:

```text
saved: thread_...
words: チーズケーキ(...) / 好き(...)
```

### Inspect the prompt

```bat
python src/threaded_concept_memory_probe.py ^
  --db reports/quickstart_llm.db ^
  --base-url http://127.0.0.1:8080 ^
  --model local-model ^
  prompt-preview "僕は何が好き？" ^
  --show-prompt
```

---

## 7. Separate Extractor and Response Models

The prototype can use separate model names for trace extraction and response generation.

```bat
python src/threaded_concept_memory_probe.py ^
  --db reports/separate_models.db ^
  --base-url http://127.0.0.1:8080 ^
  --extractor-model extractor-model ^
  --response-model response-model ^
  add "僕はチーズケーキが好きです。"
```

Use `--chat-base-url` when response generation should use a different endpoint.

```bat
python src/threaded_concept_memory_probe.py ^
  --db reports/separate_endpoints.db ^
  --base-url http://127.0.0.1:8081 ^
  --chat-base-url http://127.0.0.1:8080 ^
  --extractor-model extractor-model ^
  --response-model response-model ^
  chat
```

---

## 8. Initial Participant Recognition

The two-party conversation model uses canonical participant references:

```text
@user
@assistant
```

These are ordinary word nodes. They do not receive score boosts or identity-specific retrieval privileges.

Initialize user and assistant names:

```bat
python src/threaded_concept_memory_probe.py ^
  --db reports/participant_reference.db ^
  --base-url http://127.0.0.1:8080 ^
  --model local-model ^
  bootstrap-identity ^
  --user-name みつき ^
  --assistant-name のりこ
```

Internally, the command passes the following utterances through the normal trace creation path:

```text
user: 私の名前はみつきです。
assistant: 私の名前はのりこです。
```

Expected trace structure:

```text
@user / 名前 / みつき
@assistant / 名前 / のりこ
```

Running the same command again skips already bootstrapped traces. Use `--force` only when deliberate reinsertion is required.

### Verify participant recall

```bat
python src/threaded_concept_memory_probe.py ^
  --db reports/participant_reference.db ^
  --base-url http://127.0.0.1:8080 ^
  --model local-model ^
  --role user ^
  prompt-preview "あなたの名前は？" ^
  --show-prompt
```

Expected selection:

```text
@assistant / 名前 / のりこ
```

---

## 9. Interactive Chat

Start an interactive session:

```bat
python src/threaded_concept_memory_probe.py ^
  --db reports/chat.db ^
  --base-url http://127.0.0.1:8080 ^
  --model local-model ^
  chat
```

The exact available chat options may change during active development. Check:

```bash
python src/threaded_concept_memory_probe.py chat --help
```

---

## 10. Run an Evaluation

Evaluation scenarios are stored as JSONL files under:

```text
eval_conversations/
```

The current `eval` command requires three output paths:

- `--events-jsonl`
- `--metrics-csv`
- `--report-md`

### Recall-only evaluation

Use `--no-response` to evaluate extraction, activation, recall selection, and Working Memory without response generation.

```bat
python src/threaded_concept_memory_probe.py eval ^
  --conversation-file eval_conversations/seed_tests_public.jsonl ^
  --db reports/seed_tests.db ^
  --no-response ^
  --events-jsonl reports/seed_tests_events.jsonl ^
  --metrics-csv reports/seed_tests_metrics.csv ^
  --report-md reports/seed_tests.md
```

### LLM response-enabled evaluation

Omit `--no-response` and provide an LLM endpoint:

```bat
python src/threaded_concept_memory_probe.py eval ^
  --conversation-file eval_conversations/participant_reference_identity.jsonl ^
  --db reports/participant_reference_identity.db ^
  --base-url http://127.0.0.1:8080 ^
  --model local-model ^
  --events-jsonl reports/participant_reference_identity_events.jsonl ^
  --metrics-csv reports/participant_reference_identity_metrics.csv ^
  --report-md reports/participant_reference_identity.md
```

## Saving Prompt and Response Research Logs

Use `--research-log-jsonl` or `--research-log-dir` with `eval` to preserve the exact prompt sent to the LLM and the resulting response for each ask turn:

```bat
python src/threaded_concept_memory_probe.py eval ^
  --conversation-file eval_conversations/seed_tests_public.jsonl ^
  --db reports/research_log_eval.db ^
  --events-jsonl reports/research_log_events.jsonl ^
  --metrics-csv reports/research_log_metrics.csv ^
  --report-md reports/research_log_report.md ^
  --research-log-jsonl reports/research_log.jsonl ^
  --research-log-dir reports/research_log
```

For sensitivity runs, use `--save-research-log` to write `research_log.jsonl` and per-turn Markdown files under each trial directory:

```bat
python src/threaded_concept_memory_probe.py sensitivity ^
  --dimension prompt_view ^
  --values threadgroup,recall-state,edge ^
  --conversation-file eval_conversations/seed_tests_public.jsonl ^
  --output-dir reports/sensitivity/prompt_view_llm_v2 ^
  --save-research-log
```

Sensitivity keeps response generation disabled by default for compatibility. Add `--enable-response-generation` with an LLM endpoint when Prompt View comparisons need actual LLM responses in the research logs; `--enable-response-generation` and `--no-response` are mutually exclusive.

Research logs may contain complete user inputs, prompts, recalled traces, and LLM responses. Do not publish logs containing private conversations.

Research Logには入力、想起Trace、Prompt、LLM応答が含まれる。私的な会話を含むログを公開してはいけない。

Evaluation output includes metrics such as:

- expected hit count
- unexpected hit count
- recall precision-like score
- recall noise count
- prompt size
- Working Memory group count
- fatigue suppression
- recall efficiency
- user-origin and assistant-origin group counts

---

## 11. JSONL Scenario Format

A simple learn turn:

```json
{"turn":1,"role":"user","text":"私はチーズケーキが好きです。","mode":"learn"}
```

An assistant learn turn:

```json
{"turn":2,"role":"assistant","text":"私は紅茶が好きです。","mode":"learn"}
```

An evaluated ask turn:

```json
{
  "turn":3,
  "role":"user",
  "text":"私は何が好き？",
  "mode":"ask",
  "expected_words":["@user","チーズケーキ","好き"],
  "unexpected_words":["紅茶"]
}
```

Backward-compatible scenario files may use `user` or `assistant` fields instead of `text`, but new scenarios should prefer explicit `role` and `text`.

Common modes:

- `learn` — store the utterance as a trace
- `ask` — perform recall and generate a response unless response generation is disabled
- `ask_no_response` — perform recall without generating an LLM response

---

## 12. Inspect Stored Data

### List threads

```bat
python src/threaded_concept_memory_probe.py ^
  --db reports/quickstart_llm.db ^
  threads ^
  --limit 20 ^
  --show-source
```

### List words

```bat
python src/threaded_concept_memory_probe.py ^
  --db reports/quickstart_llm.db ^
  words
```

Use each command's `--help` output for current inspection options.

---

## 13. Prompt Views

The project supports experimental prompt representations:

```text
threadgroup
recall-state
edge
```

Select one with:

```bat
--prompt-view threadgroup
```

Example:

```bat
python src/threaded_concept_memory_probe.py ^
  --db reports/quickstart_llm.db ^
  --base-url http://127.0.0.1:8080 ^
  --model local-model ^
  --prompt-view recall-state ^
  prompt-preview "僕は何が好き？" ^
  --show-prompt
```

`threadgroup` is the compatibility default.

---

## 14. Speaker-Origin Display

Trace threads may store:

```text
created_by=user
created_by=assistant
```

This metadata records who produced the utterance that created the trace. It does not indicate who the utterance was about and does not boost recall scores.

Prompt-only origin grouping can be selected with:

```bat
--origin-order group
```

The default is:

```bat
--origin-order none
```

---

## 15. Debug LLM Extraction

Use extractor diagnostics when an expected word is missing:

```bat
python src/threaded_concept_memory_probe.py ^
  --db reports/extractor_debug.db ^
  --base-url http://127.0.0.1:8080 ^
  --model local-model ^
  --role assistant ^
  --debug-extractor ^
  add "私の名前はのりこです。"
```

The debug output includes:

- exact system prompt
- exact user message
- raw LLM response
- parsed JSON words
- Python-normalized words
- removed items
- final words

This helps distinguish an LLM extraction omission from Python-side filtering.

---

## 16. Resetting an Experiment

Each experiment should normally use a fresh SQLite database.

Windows:

```bat
del reports\quickstart.db
```

Linux / macOS:

```bash
rm -f reports/quickstart.db
```

Do not reuse a database when comparing configurations unless reuse is intentional. Existing traces, fatigue history, and reinforcement counts can change the result.

---

## 17. Running Tests

The repository test suite is runnable with the standard-library `unittest` runner:

```bash
python -m unittest discover -s tests
```

The runtime prototype itself has no third-party dependencies. Some developers may also run pytest if it is available, but pytest is not required for the documented test command.

Syntax check:

```bash
python -m py_compile src/threaded_concept_memory_probe.py
```

---

## 18. Common Problems

### `eval: error: the following arguments are required`

The current evaluation command requires:

```text
--events-jsonl
--metrics-csv
--report-md
```

Add all three output paths.

### `unrecognized arguments`

Your local branch may not include the latest change, or the option may belong before or after the subcommand.

Check:

```bash
git status
git branch
git log --oneline -5
python src/threaded_concept_memory_probe.py --help
```

Global options must generally appear before the command.

Correct:

```bat
python src/threaded_concept_memory_probe.py ^
  --db reports/test.db ^
  --debug-extractor ^
  add "..."
```

### `words:` is empty

Possible causes:

- no LLM endpoint was supplied
- the LLM endpoint is unavailable
- the LLM extractor returned no usable words
- fallback extraction found no useful surface tokens

Use `--debug-extractor` when the LLM extractor is enabled.

### LLM connection failure

Confirm that the endpoint is running and supports an OpenAI-compatible chat-completions route.

Typical endpoint:

```text
http://127.0.0.1:8080/v1/chat/completions
```

The CLI accepts the base URL and appends the compatible path used by the implementation.

### Results differ between runs

Possible causes:

- different LLM output
- reused database
- different model
- different parameter values
- fatigue history from earlier turns
- changed evaluation fixtures

For comparisons, record:

- commit SHA
- model name
- endpoint
- database path
- scenario file
- all non-default CLI options

---

## 19. Recommended First Experiments

### Experiment A: Basic preference recall

```text
Learn:
私はチーズケーキが好きです。

Ask:
私は何が好き？
```

### Experiment B: Participant reference recall

```text
Learn as user:
私の名前はみつきです。

Learn as assistant:
私の名前はのりこです。

Ask as user:
あなたの名前は？
```

### Experiment C: Third-person recall

```text
Learn:
父はコーヒーが好きです。
母はパンが好きです。

Ask:
父は何が好き？
```

These three experiments cover:

- ordinary trace recall
- two-party reference normalization
- third-person memory without participant conversion

---

## 20. Reproducibility Checklist

Before sharing a benchmark result, record:

```text
Repository commit:
Python version:
Operating system:
Extractor model:
Response model:
Base URL:
Conversation file:
Database initialized from empty:
Thread strength mode:
Prompt view:
Origin order:
Response generation enabled:
```

A benchmark result without these details may be difficult to reproduce.

---

## 21. Next Steps

After the first successful run:

1. Read `docs/02_trace_principle.md`
2. Read the architecture documents under `docs/architecture/`
3. Inspect the public evaluation scenarios under `eval_conversations/`
4. Run one scenario with `--no-response`
5. Run the same scenario with response generation enabled
6. Compare activation, Working Memory, prompt size, and response behavior

Trace Recall Engine is an active research prototype. CLI options, file names, and evaluation metrics may change as experiments continue.

---

## 9. Extractor Evaluation

Extractor evaluation is separate from conversation evaluation. It compares extractors at the extraction boundary using the same scenario JSONL, metrics CSV, detailed JSONL, and Markdown report.

```bash
python src/threaded_concept_memory_probe.py eval-extractor \
  --extractor fallback \
  --scenario eval_extractors/extractor_core_ja.jsonl \
  --metrics-csv reports/extractor_fallback.csv \
  --details-jsonl reports/extractor_fallback.jsonl \
  --report-md reports/extractor_fallback.md
```

Use `--extractor llm` with `--base-url` and `--model` to run the LLM extractor against the same scenarios.

## Local Rule Extractor v0 Status

LLM Extractor is the current baseline; fallback remains a diagnostic path. Local Rule Extractor v0 is now an experimental deterministic local candidate: it uses no morphological analyzer, no external API, and is not integrated with Android yet.

## Local Rule v0 Generalization Evaluation

Core Benchmark = development-facing baseline (`eval_extractors/extractor_core_ja.jsonl`). Generalization Benchmark = unseen-expression evaluation (`eval_extractors/extractor_generalization_ja.jsonl`). Local Rule v0 is not adopted yet; generalization results determine the next improvement scope.

The generalization benchmark is for observation, not extractor improvement in the same change. It keeps Local Rule, fallback, and LLM comparison conditions fixed, separates raw extractor output from participant-reference-normalized output, and records category summaries, novel-term retention, and long-token diagnostics so possible overfitting to the core fixture can be reviewed by humans.

## Oracle Replay Evaluator

Oracle Replay is an offline evaluator, not a production selector. It replays saved extractor Oracle details JSONL to compare fixed virtual selection strategies before implementation.

It does not alter Trace storage, Recall, or current extractor behavior. It does not change candidate generation, tokenization, gates, activation, working memory, or local-rule selection.

Its purpose is to estimate selector trade-offs before implementing them: expected-hit gain, word-count growth, unmatched added words, and counterexample risk. AIKanojyo integration remains the practical end goal; the next step after a useful replay result is to implement only the smallest promising extractor strategy and verify it downstream.

Dictionary coverage diagnostics keep DB vocabulary coverage separate from built-in protected patterns, mixed-script spans, dates, URLs, email, and other protected-span sources. If DB-derived protected matches are zero, DB dictionary coverage of zero is correct rather than a replay-adjusted score.

### Candidate Span Generator v2

Candidate Span Generator v2 adds only structurally grounded Mixed Script and safe terminal-boundary candidates. New candidates remain diagnostic-only and are not promoted to production extraction output. Oracle Replay is reused to test generalization before any selector change.

The generator records candidate `source` and `reason` metadata for oracle diagnostics while keeping final words, trace persistence, and recall behavior unchanged.
