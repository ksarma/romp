"""Runtime credentials at the SDK boundary; all providers and sessions are synthetic."""
import asyncio
import json
import os
from pathlib import Path
import sys
import tempfile
from types import ModuleType, SimpleNamespace
import unittest
from unittest.mock import patch
from importlib.machinery import SourceFileLoader

ROOT = Path(__file__).resolve().parents[1]
_IMPORT_STATE = tempfile.mkdtemp(prefix="romp-runtime-auth-")
os.environ["XDG_STATE_HOME"] = _IMPORT_STATE
os.environ.pop("ROMP_STATE_DIR", None)
os.environ["ROMP_SERVICE_ENV_FILE"] = _IMPORT_STATE + "/absent.env"
os.environ["ROMP_SERVICE_ENV"] = os.environ["ROMP_SERVICE_ENV_FILE"]
os.environ.pop("ROMP_API_KEY_REF", None)
sb = SourceFileLoader("romp_sdk_runtime_auth", str(ROOT / "kernel/sdk_backend.py")).load_module()
ks = sb._keysrc
REF = "op://test-vault/test-item/credential"
KEY = "synthetic-runtime-credential"


class RuntimeSdkAuth(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = Path(self.tmp.name) / "service.env"
        self.path.write_text("ROMP_API_KEY_REF=" + REF + "\n")
        self.env = patch.dict(os.environ, {
            "ROMP_SERVICE_ENV_FILE": str(self.path), "ROMP_SERVICE_ENV": str(self.path),
            "ROMP_API_KEY_REF": "", "ANTHROPIC_API_KEY": "synthetic-old-startup-key",
            "ANTHROPIC_AUTH_TOKEN": "synthetic-bearer", "CLAUDE_CODE_OAUTH_TOKEN": "synthetic-oauth",
        })
        self.env.start()
        self.addCleanup(self.env.stop)
        self.addCleanup(patch.stopall)
        patch.object(sb, "_WORK_KEY", None).start()
        patch.object(sb, "_STARTUP_AUTH_ENV", None).start()
        patch.object(sb, "_KEY_FILE_CHECKED", True).start()
        patch.object(ks, "_CACHE", ((), ks.KeySource("none"))).start()
        patch.object(ks, "_AUTHORITATIVE_PATHS", {}).start()
        patch.object(sb, "_FAST_ORG_VERDICTS", {}).start()
        patch.object(sb, "_fetch_key_fast_org", return_value=True).start()
        self.provider = patch.object(ks.subprocess, "run", return_value=SimpleNamespace(
            returncode=0, stdout=KEY.encode())).start()
        fake_sdk = ModuleType("claude_agent_sdk")
        fake_sdk.HookMatcher = lambda **kw: kw
        fake_sdk.ClaudeAgentOptions = dict
        fake_sdk.ClaudeSDKClient = unittest.mock.Mock()
        for name in ("AssistantMessage", "ResultMessage", "SystemMessage"):
            setattr(fake_sdk, name, type(name, (), {}))
        self.client_factory = fake_sdk.ClaudeSDKClient
        patch.dict(sys.modules, {"claude_agent_sdk": fake_sdk}).start()
        self.logs = []
        self.be = sb.SdkBackend(str(Path(self.tmp.name) / "state"), "/bin/true",
                                lambda *a, **k: None, log=self.logs.append)

    def session(self, auth="", **extra):
        sid = self.be.spawn("synthetic", "/tmp", auth=auth)
        reg = sb.read_reg(self.be.state_dir, sid)
        reg.update(extra)
        return sb.SdkSession(self.be, reg)

    def test_ui_defaults_and_auth_selection_never_retrieve_a_key(self):
        sess = self.session()
        for _ in range(3):
            self.assertTrue(self.be.work_key_configured)
            self.assertEqual(self.be.work_key_source_fp(), ks.KeySource("op", REF).fingerprint())
            self.assertEqual(self.be.default_auth({}), "key")
            self.assertEqual(sess.effective_auth(), "key")
            self.assertEqual(sess.snapshot()["auth"], "key")
        self.assertTrue(self.be.set_auth(sess.sid, "key"))
        self.provider.assert_not_called()
        self.assertEqual(sb._WORK_KEY, "", "the replaced startup key is discarded")

    def test_each_key_launch_resolves_once_and_keeps_secrets_out_of_files_and_caches(self):
        self.provider.side_effect = [SimpleNamespace(returncode=0, stdout=KEY.encode()),
                                    SimpleNamespace(returncode=0, stdout=b"synthetic-rotated-key")]
        sess = self.session("key", env={"FEATURE_FLAG": "yes"})
        first = self.be._options(sess, dict)
        second = self.be._options(sess, dict)
        self.assertEqual(first["env"]["ANTHROPIC_API_KEY"], KEY)
        self.assertEqual(second["env"]["ANTHROPIC_API_KEY"], "synthetic-rotated-key")
        self.assertEqual(self.provider.call_count, 2)
        self.assertEqual(self.provider.call_args.args[0], ["op", "read", "--no-newline", REF])
        for name in sb.AUTH_ENV_NAMES:
            self.assertNotIn(name, os.environ)
        for name in sb.AUTH_ENV_NAMES[1:]:
            self.assertNotIn(name, first["env"])
        self.assertEqual(sb._WORK_KEY, "")
        self.assertNotIn(KEY, repr(sb._FAST_ORG_VERDICTS))
        for file in Path(self.tmp.name).rglob("*"):
            if file.is_file():
                self.assertNotIn(KEY.encode(), file.read_bytes(), str(file))
        self.assertNotIn(KEY, "\n".join(self.logs))

    def test_login_does_not_invoke_a_broken_provider_and_restores_only_login_tokens(self):
        self.provider.side_effect = FileNotFoundError()
        options = self.be._options(self.session("login"), dict)
        self.provider.assert_not_called()
        self.assertNotIn("ANTHROPIC_API_KEY", options["env"])
        self.assertEqual(options["env"]["ANTHROPIC_AUTH_TOKEN"], "synthetic-bearer")
        self.assertEqual(options["env"]["CLAUDE_CODE_OAUTH_TOKEN"], "synthetic-oauth")

    def test_failed_runtime_retrieval_never_constructs_a_client_and_records_launch_error(self):
        self.provider.return_value = SimpleNamespace(returncode=1, stdout=b"provider-output-must-not-leak")
        sess = self.session("key")
        with patch.object(self.be, "_record_launch_error") as record:
            with self.assertRaises(ks.KeySourceError):
                asyncio.run(sess._amain())
        record.assert_called_once()
        self.client_factory.assert_not_called()
        self.assertEqual(sess.effective_auth(), "key")
        self.assertNotIn("provider-output", str(record.call_args))

    def test_empty_explicit_key_refuses_login_fallback(self):
        self.be.work_key = ""
        sess = self.session("key")
        self.assertEqual(sess.effective_auth(), "key")
        with self.assertRaisesRegex(ks.KeySourceError, "no API key source"):
            self.be._options(sess, dict)
        self.provider.assert_not_called()

    def test_provider_failure_record_does_not_reuse_a_previous_clis_stderr(self):
        sess = self.session("key")
        with patch.object(sess, "stderr_tail", return_value="old CLI output"):
            self.be._record_launch_error(sess, ks.KeySourceError("1Password credential retrieval failed"))
        error = sb.read_reg(self.be.state_dir, sess.sid)["launchError"]
        self.assertIn("1Password credential retrieval failed", error["text"])
        self.assertNotIn("old CLI output", error["text"])

    def test_removed_runtime_reference_keeps_the_failure_explicit(self):
        self.path.write_text("ROMP_PERF=1\n")
        self.assertTrue(self.be.work_key_configured)
        with self.assertRaises(ks.KeySourceError):
            self.be._options(self.session(), dict)
        self.provider.assert_not_called()

    def test_runtime_mode_refuses_new_persisted_credentials_and_filters_legacy_settings(self):
        for name in sb.AUTH_ENV_NAMES:
            self.assertIn("reserved", sb.env_request_error({name: "synthetic-legacy-secret"}))
            with self.assertRaisesRegex(ValueError, "reserved"):
                self.be.spawn("bad", "/tmp", env={name: "synthetic-legacy-secret"})
        sess = self.session("key", env={**{name: "synthetic-legacy-secret" for name in sb.AUTH_ENV_NAMES},
                                        "FEATURE_FLAG": "yes"})
        options = self.be._options(sess, dict)
        saved_env = json.loads(Path(options["settings"]).read_text())["env"]
        self.assertEqual(saved_env, {"FEATURE_FLAG": "yes"})

    def test_cycles_skip_login_dormant_and_busy_sessions_before_retrieval(self):
        login = self.session("login")
        self.be.sessions[login.sid] = login
        dormant = self.session("key")
        busy = self.session("key")
        self.be.sessions[busy.sid] = busy
        busy.inflight = 1
        self.assertEqual(self.be.cycle_key(login.sid), "login")
        self.assertEqual(self.be.cycle_key(dormant.sid), "dormant")
        self.assertEqual(self.be.cycle_key(busy.sid), "working")
        self.provider.assert_not_called()

    def test_cycle_resolves_once_for_currentness_and_logging(self):
        sess = self.session("key")
        self.be.sessions[sess.sid] = sess
        with patch.object(sess, "request_reconnect") as reconnect:
            self.assertEqual(self.be.cycle_key(sess.sid), "cycling")
        reconnect.assert_called_once_with(defer=False)
        self.assertEqual(self.provider.call_count, 1)
        sess._launched_key_fp = ks.fingerprint(KEY)
        with patch.object(sess, "request_reconnect") as reconnect:
            self.assertEqual(self.be.cycle_key(sess.sid), "current")
        reconnect.assert_not_called()
        self.assertEqual(self.provider.call_count, 2)


if __name__ == "__main__":
    unittest.main()
