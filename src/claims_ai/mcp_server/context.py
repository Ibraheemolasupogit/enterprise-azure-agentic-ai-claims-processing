"""Read-once private host context; RPC content never constructs or replaces grants."""

import os
import stat
from hashlib import sha256
from pathlib import Path

from claims_ai.agent_tools.tools import authorize
from claims_ai.agents.__main__ import demo_input
from claims_ai.agents.contracts import AssessmentInput
from claims_ai.mcp_server.contracts import HostConfiguration


def read_configuration(path: Path) -> HostConfiguration:
    parent = path.parent
    info = parent.stat(follow_symlinks=False)
    if not stat.S_ISDIR(info.st_mode) or info.st_uid != os.geteuid() or info.st_mode & 0o077:
        raise ValueError("host context requires a private owned directory")
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    with os.fdopen(fd, "rb") as stream:
        info = os.fstat(stream.fileno())
        if (
            not stat.S_ISREG(info.st_mode)
            or info.st_uid != os.geteuid()
            or info.st_mode & 0o077
            or info.st_nlink != 1
            or info.st_size > 16384
        ):
            raise ValueError("host context is not a bounded private regular file")
        content = stream.read(16385)
    if len(content) > 16384:
        raise ValueError("host context limit exceeded")
    return HostConfiguration.model_validate_json(content)


def load_context(path: Path | None) -> tuple[HostConfiguration | None, AssessmentInput | None]:
    """Invalid/missing configuration stays denied; exceptions never become protocol text."""
    if path is None:
        return None, None
    try:
        config = read_configuration(path)
        if config.grant is None:
            return None, None
        root = config.fixture_root
        if sha256((root / "manifest.json").read_bytes()).hexdigest() != config.manifest_sha256:
            return None, None
        value = demo_input(root, config.fixture_id)
        if not authorize(value, config.grant):
            return None, None
        return config, value
    except (OSError, ValueError, StopIteration):
        return None, None
