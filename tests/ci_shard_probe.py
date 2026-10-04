"""A pytest plugin for tests/test_ci_shards.py's census, loaded with -p tests.ci_shard_probe in its child runs.

The census asks pytest which test files a run collects, once with no shard and once for each shard, and a real
collection of this suite imports every test module: on 2026-10-04 one took 696 s and more than 5 GB on a loaded
machine, too much to run SHARD_COUNT + 1 times inside the suite. This plugin stands in at the one step after the
selection: pytest_pycollect_makemodule, which pytest calls for each file it has decided to make a test module of,
after pytest_ignore_collect (where tests/conftest.py drops another shard's files) and its own python_files match.
Here that call returns a file node holding one placeholder item instead of the module, so nothing is imported, and
`pytest --collect-only -q` lists one line per collected file, `<path>::ci-shard-probe`. Every step before it, the
conftest's selection among them, runs as it does in CI's run.
"""
import pytest

PROBE_ITEM = "ci-shard-probe"


class _ProbeItem(pytest.Item):
    def runtest(self):
        pass


class _UnimportedFile(pytest.File):
    def collect(self):
        return [_ProbeItem.from_parent(self, name=PROBE_ITEM)]


@pytest.hookimpl(tryfirst=True)
def pytest_pycollect_makemodule(module_path, parent):
    return _UnimportedFile.from_parent(parent, path=module_path)
