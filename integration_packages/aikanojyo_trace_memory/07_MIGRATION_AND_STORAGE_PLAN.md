# Migration and Storage Plan

- Add Trace tables; do not modify existing AIKanojyo memory tables destructively.
- Save one conversation turn in one transaction.
- Maintain a Trace vocabulary cache; invalidate after insert; rebuild on restart; watch Android memory.
- Track word rows, thread rows, link rows, average words/thread, unique words, and DB size.
- Do not rush retention deletion in initial Shadow; observe growth first.
- Back up user data before migration and keep rollback possible.
