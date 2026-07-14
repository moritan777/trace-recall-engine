# Shadow Mode Plan

## Definition
Existing AIKanojyo Memory makes production responses. Trace Engine runs in parallel, writes logs only, is not inserted into the prompt, and does not affect user experience.

## Log per turn
turn id, input, created_by, extracted words, created threads, recalled words, recalled thread groups, gate output, prompt candidate, processing time, errors.

## Compare
Existing Memory Recall vs Trace Recall: overlap, only-existing, only-trace, empty, noise, important memory miss.

## Duration
Start with 300T; prefer 500T; extend to 1000T if growth/noise is unclear.

## Exit conditions
No crash, no uncontrolled DB growth, stable prompt candidate size, tolerable recall noise, no major misses for names/birthdays/corrections, and multiple useful real-conversation examples.
