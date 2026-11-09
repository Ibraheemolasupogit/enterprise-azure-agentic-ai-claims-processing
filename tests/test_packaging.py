"""Installed-package discovery must work independently of pytest's source path."""

import os
import subprocess
import sys
from pathlib import Path


def test_installed_package_imports_without_pythonpath_from_other_cwd(tmp_path: Path) -> None:
    result = subprocess.run(
        [
            sys.executable,
            "-I",
            "-B",
            "-c",
            "from importlib.metadata import version; "
            "import claims_ai; "
            "import claims_ai.mcp_http.transport; "
            "import claims_ai.mcp_http.policy_validation; "
            "assert claims_ai.__version__ == version('northstar-claims-ai'); "
            "print('installed imports verified')",
        ],
        cwd=tmp_path,
        env={key: value for key, value in os.environ.items() if key != "PYTHONPATH"},
        capture_output=True,
        text=True,
        timeout=15,
    )
    assert result.returncode == 0, result.stderr
    assert result.stdout == "installed imports verified\n"
