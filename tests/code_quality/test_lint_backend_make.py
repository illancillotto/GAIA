import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]


@pytest.mark.parametrize("compile_exit", [0, 3])
def test_lint_backend_isolates_and_cleans_bytecode_cache(tmp_path, compile_exit):
    interpreter = tmp_path / "interpreter.py"
    interpreter.write_text(
        "import os, sys\n"
        "from pathlib import Path\n"
        "record = Path(os.environ['LINT_TEST_RECORD'])\n"
        "if '-m' in sys.argv:\n"
        "    cache = Path(os.environ['PYTHONPYCACHEPREFIX'])\n"
        "    assert cache.is_dir()\n"
        "    record.write_text(str(cache))\n"
        "    (cache / 'test.pyc').write_bytes(b'bytecode')\n"
        "    raise SystemExit(int(os.environ['LINT_TEST_COMPILE_EXIT']))\n"
        "assert not Path(record.read_text()).exists()\n"
        "record.with_suffix('.style').write_text('style checked')\n"
    )
    record = tmp_path / "cache-path.txt"
    result = subprocess.run(
        ["make", "lint-backend", f"QUALITY_PYTHON={sys.executable} {interpreter}"],
        cwd=ROOT,
        env={
            **os.environ,
            "LINT_TEST_RECORD": str(record),
            "LINT_TEST_COMPILE_EXIT": str(compile_exit),
        },
        capture_output=True,
        text=True,
    )
    assert (result.returncode == 0) == (compile_exit == 0), result.stderr
    assert not Path(record.read_text()).exists()
    assert record.with_suffix(".style").exists() == (compile_exit == 0)
