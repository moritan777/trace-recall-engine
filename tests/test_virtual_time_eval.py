import datetime as dt
import unittest

from virtual_time_eval import VirtualEvalClock, parse_virtual_args


class VirtualTimeEvalTests(unittest.TestCase):
    def test_virtual_clock_advances_one_day_per_ten_turns(self):
        clock = VirtualEvalClock(dt.datetime(2026, 1, 1, 0, 0, 0), 10)

        self.assertEqual(clock.now, dt.datetime(2026, 1, 1, 0, 0, 0))

        for _ in range(10):
            clock.advance_turn()

        self.assertEqual(clock.now, dt.datetime(2026, 1, 2, 0, 0, 0))

        for _ in range(9990):
            clock.advance_turn()

        self.assertEqual(clock.completed_turns, 10000)
        self.assertEqual(clock.now, dt.datetime(2028, 9, 27, 0, 0, 0))

    def test_parse_virtual_args_preserves_probe_eval_args(self):
        virtual, remaining = parse_virtual_args(
            [
                "--virtual-turns-per-day",
                "10",
                "--virtual-start",
                "2026-01-01T00:00:00",
                "--conversation-file",
                "fixture.jsonl",
                "--no-response",
            ]
        )

        self.assertEqual(virtual.virtual_turns_per_day, 10)
        self.assertEqual(virtual.virtual_start_dt, dt.datetime(2026, 1, 1, 0, 0, 0))
        self.assertEqual(remaining, ["--conversation-file", "fixture.jsonl", "--no-response"])


if __name__ == "__main__":
    unittest.main()
