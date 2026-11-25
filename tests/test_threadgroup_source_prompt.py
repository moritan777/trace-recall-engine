import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
import threaded_concept_memory_probe as p

class ThreadGroupSourcePromptTests(unittest.TestCase):
    def group(self):
        return p.GatedThreadGroup(
            canonical_key="元カノ|苦手|話", representative_thread_id="t1", occurrence_count=1,
            score=1.0, group_score=1.0, base_score=1.0, common_bonus=0.0, effective_strength=1.0,
            words=["元カノ","苦手","話"], direct_words=["元カノ"], core_words=["元カノ","苦手","話"],
            support_words=[], suppressed_words=[], member_thread_ids=["t1"],
            created_by_counts={"user":1}, dominant_created_by="user",
            source_texts=["元カノの話はまだ苦手"],
        )
    def context(self):
        return p.GatedContext(threads=[self.group()], words=[], suppressed_words=[], summary="selected")
    def test_baseline_threadgroup_does_not_expose_source(self):
        text="\n".join(p.format_gated_recall_context(self.context(), "threadgroup"))
        self.assertNotIn("元カノの話はまだ苦手", text)
    def test_threadgroup_source_exposes_verbatim_source(self):
        text="\n".join(p.format_gated_recall_context(self.context(), "threadgroup-source"))
        self.assertIn('source="元カノの話はまだ苦手"', text)
    def test_normalizer_accepts_new_view(self):
        self.assertEqual(p.normalize_prompt_view("threadgroup-source"), "threadgroup-source")

if __name__ == "__main__": unittest.main()
