# Data Model

## WordNode / words table (Verified)
Fields: word_id TEXT PRIMARY KEY, word TEXT UNIQUE NOT NULL, strength REAL, weight REAL, seen_count INTEGER, first_seen TEXT, last_seen TEXT.

## Thread / threads table (Verified)
Fields: thread_id TEXT PRIMARY KEY, date TEXT, source_text TEXT, canonical_key TEXT, strength REAL, created_at TEXT, last_seen TEXT, seen_count INTEGER, created_by TEXT DEFAULT 'user'. created_by values are normalized to user or assistant.

## WordThreadLink / word_threads table (Verified)
Fields: word_id TEXT, thread_id TEXT, weight_in_thread REAL, added_at TEXT, PRIMARY KEY(word_id, thread_id), foreign keys to words and threads.

## Conversation exposures (Verified)
Fields: id TEXT, word TEXT, thread_id TEXT, canonical_key TEXT, exposure_type TEXT DEFAULT 'prompt', exposed_at TEXT, turn_no INTEGER. Used for fatigue.

## Constraints and count mode
- Same normalized word is unique in words.
- Count mode creates independent experience threads; repeated experiences are not collapsed into one weight.
- Prompt groups repeated same canonical_key as ThreadGroup only at presentation time.

## AIKanojyo migration principles
Add new Trace tables beside existing AIKanojyo tables; never destructively alter existing user memory; make migrations reversible/backed up; in Shadow Mode do not affect existing memory.
