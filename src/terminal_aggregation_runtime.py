from __future__ import annotations

import math
import time
from dataclasses import dataclass
from typing import Any

import threaded_concept_memory_probe as probe


@dataclass
class TerminalAggregationRuntimeStats:
    enabled: bool = True
    physical_terminal_paths: int = 0
    distinct_terminal_edges: int = 0
    maximum_edge_multiplicity: int = 0
    activation_elapsed_ms: float = 0.0

    @property
    def operations_saved(self) -> int:
        return self.physical_terminal_paths - self.distinct_terminal_edges

    @property
    def aggregation_ratio(self) -> float:
        if self.distinct_terminal_edges <= 0:
            return 1.0
        return self.physical_terminal_paths / self.distinct_terminal_edges


class TerminalAggregationActivationEngine(probe.ActivationEngine):
    """Opt-in runtime prototype aggregating only terminal word->thread work.

    Storage, traversal depth, pre-terminal propagation, Gate, Fatigue,
    Reinforcement, ThreadGroup selection and Working Memory are unchanged.
    """

    cumulative_stats = TerminalAggregationRuntimeStats()

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.last_terminal_aggregation_stats = TerminalAggregationRuntimeStats()

    def activate(self, input_words: list[probe.ExtractedWord], top_words: int = 20, top_threads: int = 8) -> probe.ActivationResult:
        started = time.perf_counter()
        now = probe.now_iso()
        known_words = self.store.get_all_words()
        direct_input_word_set = {probe.normalize_word(w.word) for w in input_words if probe.normalize_word(w.word)}

        word_scores: dict[str, float] = {}
        word_best_depth: dict[str, int] = {}
        word_threads: dict[str, set[str]] = {}
        word_activated_by: dict[str, list[str]] = {}
        thread_base_scores: dict[str, float] = {}
        thread_scores: dict[str, float] = {}
        thread_matched_words: dict[str, set[str]] = {}
        thread_direct_matched_words: dict[str, set[str]] = {}
        thread_activated_by: dict[str, list[str]] = {}
        thread_common_bonus: dict[str, float] = {}
        traces: list[probe.ActivationTrace] = []
        queue: list[tuple[str, str, float, int]] = []
        visited_word_score: dict[str, float] = {}
        visited_thread_score: dict[str, float] = {}

        # Every physical score reaching a terminal word is retained here.  The
        # invariant outgoing edge factor is applied once per distinct edge.
        terminal_inputs: dict[str, list[float]] = {}

        def record_trace(from_type: str, from_id: str, to_type: str, to_id: str, depth: int, score: float, reason: str) -> None:
            traces.append(probe.ActivationTrace(from_type, from_id, to_type, to_id, depth, score, reason))

        for iw in input_words:
            for matched_word, sim in probe.match_known_words(iw.word, known_words):
                node = self.store.get_word_by_text(matched_word)
                if node is None:
                    continue
                score = self._word_score(node, iw.weight * sim, depth=0, now=now)
                probe.add_word_activation(word_scores, word_best_depth, word_threads, word_activated_by, node.word, [], score, 0, f"input:{iw.word}")
                record_trace("input", iw.word, "word", node.word, 0, score, f"matched sim={sim:.2f}")
                if score > visited_word_score.get(node.word_id, 0.0):
                    visited_word_score[node.word_id] = score
                    queue.append(("word", node.word_id, score, 0))

        while queue:
            node_type, node_id, score, depth = queue.pop(0)
            if depth >= self.max_depth:
                continue
            next_depth = depth + 1

            if node_type == "word":
                node = self.store.get_word_by_id(node_id)
                if node is None:
                    continue

                if next_depth == self.max_depth:
                    terminal_inputs.setdefault(node_id, []).append(score)
                    continue

                for link in self.store.get_links_for_word(node_id):
                    thread = self.store.get_thread(link.thread_id)
                    if thread is None:
                        continue
                    effective_strength = self._thread_effective_strength(thread, now)
                    thread_score = score * link.weight_in_thread * effective_strength * probe.DEPTH_DECAY.get(next_depth, 0.03)
                    if thread_score <= 0.001:
                        continue
                    thread_base_scores[link.thread_id] = thread_base_scores.get(link.thread_id, 0.0) + thread_score
                    thread_matched_words.setdefault(link.thread_id, set()).add(node.word)
                    if node.word in direct_input_word_set:
                        thread_direct_matched_words.setdefault(link.thread_id, set()).add(node.word)
                    probe.add_activated_by(thread_activated_by, link.thread_id, f"word:{node.word}")
                    record_trace("word", node.word, "thread", link.thread_id, next_depth, thread_score, "word->thread")
                    if thread_score > visited_thread_score.get(link.thread_id, 0.0):
                        visited_thread_score[link.thread_id] = thread_score
                        queue.append(("thread", link.thread_id, thread_score, next_depth))

            elif node_type == "thread":
                thread_id = node_id
                for link in self.store.get_links_for_thread(thread_id):
                    node = self.store.get_word_by_id(link.word_id)
                    if node is None:
                        continue
                    word_score = self._word_score(node, score * link.weight_in_thread, depth=next_depth, now=now)
                    if word_score <= 0.001:
                        continue
                    probe.add_word_activation(word_scores, word_best_depth, word_threads, word_activated_by, node.word, [thread_id], word_score, next_depth, f"thread:{thread_id}")
                    record_trace("thread", thread_id, "word", node.word, next_depth, word_score, "thread->word")
                    if word_score > visited_word_score.get(node.word_id, 0.0):
                        visited_word_score[node.word_id] = word_score
                        queue.append(("word", node.word_id, word_score, next_depth))

        terminal_stats = TerminalAggregationRuntimeStats()
        terminal_decay = probe.DEPTH_DECAY.get(self.max_depth, 0.03)
        for node_id, physical_scores in terminal_inputs.items():
            node = self.store.get_word_by_id(node_id)
            if node is None:
                continue
            for link in self.store.get_links_for_word(node_id):
                thread = self.store.get_thread(link.thread_id)
                if thread is None:
                    continue
                factor = link.weight_in_thread * self._thread_effective_strength(thread, now) * terminal_decay
                if factor <= 0:
                    continue
                cutoff = 0.001 / factor
                accepted_scores = [value for value in physical_scores if value > cutoff]
                if not accepted_scores:
                    continue
                multiplicity = len(accepted_scores)
                thread_score = math.fsum(accepted_scores) * factor
                terminal_stats.physical_terminal_paths += multiplicity
                terminal_stats.distinct_terminal_edges += 1
                terminal_stats.maximum_edge_multiplicity = max(terminal_stats.maximum_edge_multiplicity, multiplicity)
                thread_base_scores[link.thread_id] = thread_base_scores.get(link.thread_id, 0.0) + thread_score
                thread_matched_words.setdefault(link.thread_id, set()).add(node.word)
                if node.word in direct_input_word_set:
                    thread_direct_matched_words.setdefault(link.thread_id, set()).add(node.word)
                probe.add_activated_by(thread_activated_by, link.thread_id, f"word:{node.word}")
                record_trace("word", node.word, "thread", link.thread_id, self.max_depth, thread_score, f"word->thread terminal-aggregated multiplicity={multiplicity}")

        for thread_id, base in thread_base_scores.items():
            direct_count = len(thread_direct_matched_words.get(thread_id, set()))
            common_bonus = base * self.common_bonus_multiplier * ((direct_count - 1) ** 2) if direct_count >= 2 else 0.0
            thread_common_bonus[thread_id] = common_bonus
            thread_scores[thread_id] = base + common_bonus
            if common_bonus > 0:
                record_trace("thread", thread_id, "thread", thread_id, 0, common_bonus, f"common-bonus direct_matches={direct_count}")

        for thread_id, final_score in thread_scores.items():
            if final_score <= 0:
                continue
            direct_count = len(thread_direct_matched_words.get(thread_id, set()))
            if direct_count <= 0:
                continue
            thread = self.store.get_thread(thread_id)
            if thread is None:
                continue
            joint_factor = 1.0 + max(0, direct_count - 1)
            for link in self.store.get_links_for_thread(thread_id):
                node = self.store.get_word_by_id(link.word_id)
                if node is None or node.word in direct_input_word_set:
                    continue
                boost = final_score * self.mutual_amplification * link.weight_in_thread * 0.10 * joint_factor
                if boost <= 0.001:
                    continue
                probe.add_word_activation(word_scores, word_best_depth, word_threads, word_activated_by, node.word, [thread_id], boost, 2, f"mutual:{thread_id}")
                record_trace("thread", thread_id, "word", node.word, 2, boost, "mutual-amplification")

        activated_words = [
            probe.ActivatedWord(word=w, score=s, best_depth=word_best_depth.get(w, 99), thread_ids=sorted(word_threads.get(w, set())), activated_by=word_activated_by.get(w, [])[:6])
            for w, s in sorted(word_scores.items(), key=lambda kv: kv[1], reverse=True) if s > 0.001
        ][:top_words]

        activated_threads: list[probe.ActivatedThread] = []
        for thread_id, score in sorted(thread_scores.items(), key=lambda kv: kv[1], reverse=True)[:top_threads]:
            thread = self.store.get_thread(thread_id)
            if thread is None:
                continue
            activated_threads.append(probe.ActivatedThread(
                thread_id=thread_id, score=score, base_score=thread_base_scores.get(thread_id, 0.0),
                common_bonus=thread_common_bonus.get(thread_id, 0.0), words=thread.words,
                matched_words=sorted(thread_matched_words.get(thread_id, set())),
                activated_by=thread_activated_by.get(thread_id, [])[:8], date=thread.date,
                canonical_key=thread.canonical_key, thread_strength=thread.strength,
                effective_strength=self._thread_effective_strength(thread, now),
                same_key_thread_count=self.store.count_threads_by_canonical_key(thread.canonical_key),
                created_by=thread.created_by,
            ))

        terminal_stats.activation_elapsed_ms = (time.perf_counter() - started) * 1000.0
        self.last_terminal_aggregation_stats = terminal_stats
        cumulative = type(self).cumulative_stats
        cumulative.physical_terminal_paths += terminal_stats.physical_terminal_paths
        cumulative.distinct_terminal_edges += terminal_stats.distinct_terminal_edges
        cumulative.maximum_edge_multiplicity = max(cumulative.maximum_edge_multiplicity, terminal_stats.maximum_edge_multiplicity)
        cumulative.activation_elapsed_ms += terminal_stats.activation_elapsed_ms
        return probe.ActivationResult(input_words, activated_words, activated_threads, traces)
