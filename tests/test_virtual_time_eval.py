import datetime as dt
import importlib.util
from pathlib import Path


MODULE_PATH = Path(__file__).resolve().parents[1] / "src" / "virtual_time_eval.py"
spec = importlib.util.spec_from_file_location("virtual_time_eval", MODULE_PATH)
virtual_time_eval = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(virtual_time_eval)


VirtualEvalClock = virtual_time_eval.VirtualEvalClock
parse_virtual_args = virtual_time_eval.parse_virtual_args


def test_virtual_clock_advances_one_day_per_ten_turns():
    clock = VirtualEvalClock(dt.datetime(2026, 1, 1, 0, 0, 0), 10)

    assert clock.now == dt.datetime(2026, 1, 1, 0, 0, 0)

    for _ in range(10):
        clock.advance_turn()

    assert clock.now == dt.datetime(2026, 1, 2, 0, 0, 0)

    for _ in range(9990):
        clock.advance_turn()

    assert clock.completed_turns == 10000
    assert clock.now == dt.datetime(2028, 9, 27, 0, 0, 0)


def test_parse_virtual_args_preserves_probe_eval_args():
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

    assert virtual.virtual_turns_per_day == 10
    assert virtual.virtual_start_dt == dt.datetime(2026, 1, 1, 0, 0, 0)
    assert remaining == ["--conversation-file", "fixture.jsonl", "--no-response"]
