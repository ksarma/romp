"""Fast mode's statusline word (the user 2026-08-07). The CLI refuses fast mode to any non-interactive
client unless the session opts in through the flag-settings layer, so romp opts in per session and shows
the result on a chip beside model and effort.

The chip's label is decided by _fast_word, and its whole job is to not lie: what the CLI REPORTS beats
what romp asked for, because the two really do come apart (fast mode needs an Opus model and carries its
own rate limit). "" means the session has no fast mode at all — a tmux pane — and the chip stays away."""
import os
import unittest
from importlib.machinery import SourceFileLoader

HERE = os.path.dirname(os.path.realpath(__file__))
BIN = os.path.join(os.path.dirname(HERE), "bin")
os.environ["ROMP_KERNEL_NO_OPEN"] = "1"
os.environ.setdefault("ROMP_SERVE_TOKEN", "testtok")
km = SourceFileLoader("romp_kernel_fastmode", os.path.join(BIN, "romp-kernel")).load_module()


class FastWord(unittest.TestCase):
    def test_a_session_with_no_fast_mode_gets_no_chip(self):
        # a tmux pane's status carries no 'fast' key at all — there is no flag-settings layer behind it
        self.assertEqual(km._fast_word({"model": "Opus 5", "effort": "high"}), "")
        self.assertEqual(km._fast_word(None), "")

    def test_the_request_stands_in_until_the_cli_has_reported(self):
        # the CLI emits no init on a turn-less connect, so a session that hasn't run anything has no
        # report yet — saying what was asked for is the honest answer, and it is what the user picked
        self.assertEqual(km._fast_word({"fast": True, "fastState": ""}), "on")
        self.assertEqual(km._fast_word({"fast": False, "fastState": ""}), "off")

    def test_the_cli_report_overrides_the_request(self):
        # opted in, but the CLI declined (wrong model, no credits): the badge must show what is TRUE
        self.assertEqual(km._fast_word({"fast": True, "fastState": "off"}), "off")
        self.assertEqual(km._fast_word({"fast": False, "fastState": "on"}), "on")

    def test_cooldown_reaches_the_chip(self):
        # fast mode's own rate limit — the session is running normally and nothing else would say so
        self.assertEqual(km._fast_word({"fast": True, "fastState": "cooldown"}), "cooldown")

    def test_a_word_the_cli_never_promised_falls_back_to_the_request(self):
        # a future CLI state romp has no label for must not reach the chip as mystery text
        self.assertEqual(km._fast_word({"fast": True, "fastState": "warp-nine"}), "on")


class FastModeIsSdkOnly(unittest.TestCase):
    def test_the_drive_op_is_registered(self):
        import inspect
        self.assertIn('"setFast"', inspect.getsource(km._drive))

    def test_the_park_queue_understands_the_fast_op(self):
        import inspect
        self.assertIn('elif op[0] == "fast":', inspect.getsource(km._apply_pending_ops))


if __name__ == "__main__":
    unittest.main()
