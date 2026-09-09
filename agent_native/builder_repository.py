"""Narrow host-side repository operations for the protected First Builder."""

import hashlib
import os
from pathlib import Path, PurePosixPath
import subprocess
import tempfile


MAX_FILE_BYTES = 256_000
MAX_OUTPUT_BYTES = 128_000
_GIT_READ = frozenset({"status", "diff", "log", "show", "rev-parse", "branch"})
_GIT_WRITE = frozenset({"add", "commit"})


def _root(root):
    root = Path(root)
    if root.is_symlink() or not root.is_dir():
        raise ValueError("Builder repository is unavailable")
    return root.resolve()


def _relative(value):
    if not isinstance(value, str) or not value or "\x00" in value:
        raise ValueError("Repository path must be nonblank text")
    path = PurePosixPath(value)
    if path.is_absolute() or ".." in path.parts or value.startswith("~"):
        raise PermissionError("Repository path escapes the granted root")
    return path


def _path(root, value, *, existing=False):
    root = _root(root)
    relative = _relative(value)
    target = root.joinpath(*relative.parts)
    current = root
    for part in relative.parts[:-1] if not existing else relative.parts:
        current = current / part
        if current.is_symlink():
            raise PermissionError("Repository symlinks are outside the Builder file grant")
    if existing and (target.is_symlink() or not target.is_file()):
        raise ValueError("Repository file does not exist")
    if not existing and target.exists() and (target.is_symlink() or not target.is_file()):
        raise ValueError("Repository destination is not a regular file")
    return root, target


def _digest(body):
    return hashlib.sha256(body).hexdigest()


def read_file(root, arguments):
    if not isinstance(arguments, dict) or set(arguments) != {"path"}:
        raise ValueError("repository_file_read requires path")
    _, path = _path(root, arguments["path"], existing=True)
    body = path.read_bytes()
    if len(body) > MAX_FILE_BYTES:
        raise ValueError("Repository file exceeds the read limit")
    try:
        content = body.decode("utf-8")
    except UnicodeDecodeError:
        raise ValueError("Repository file must be UTF-8 text") from None
    return {"path": arguments["path"], "content": content, "sha256": _digest(body)}


def write_file(root, arguments):
    if (not isinstance(arguments, dict)
            or set(arguments) != {"path", "content", "expected_sha256"}
            or not isinstance(arguments["content"], str)
            or len(arguments["content"].encode()) > MAX_FILE_BYTES
            or not isinstance(arguments["expected_sha256"], str)):
        raise ValueError("repository_file_write requires path, UTF-8 content and expected_sha256")
    _, path = _path(root, arguments["path"])
    if not path.exists():
        if arguments["expected_sha256"] != "missing":
            raise ValueError("Repository file changed; read it again")
    elif _digest(path.read_bytes()) != arguments["expected_sha256"]:
        raise ValueError("Repository file changed; read it again")
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.parent.is_symlink():
        raise PermissionError("Repository symlinks are outside the Builder file grant")
    body = arguments["content"].encode()
    fd, temporary = tempfile.mkstemp(prefix=".agent-native-write-", dir=path.parent)
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(body)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)
    return {"path": arguments["path"], "sha256": _digest(body), "bytes": len(body)}


def _allowed(argv):
    if not isinstance(argv, list) or not 1 <= len(argv) <= 64 or any(
            not isinstance(value, str) or not value or "\x00" in value or len(value) > 4096
            for value in argv):
        return False
    executable = argv[0]
    if executable == "rg":
        return True
    if executable == "git" and len(argv) >= 2:
        return argv[1] in _GIT_READ | _GIT_WRITE
    if executable in {".venv/bin/pytest", ".venv/bin/python", "npm", "node"}:
        return True
    return False


def command(root, arguments):
    if (not isinstance(arguments, dict) or set(arguments) - {"argv", "timeout_seconds"}
            or not _allowed(arguments.get("argv"))):
        raise PermissionError("Repository command is outside the Builder development grant")
    timeout = arguments.get("timeout_seconds", 30)
    if type(timeout) is not int or not 1 <= timeout <= 180:
        raise ValueError("Repository command timeout must be 1–180 seconds")
    root = _root(root)
    try:
        result = subprocess.run(arguments["argv"], cwd=root, stdin=subprocess.DEVNULL,
                                stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                timeout=timeout, env={"PATH": os.environ.get("PATH", "")})
        body = result.stdout
        truncated = len(body) > MAX_OUTPUT_BYTES
        return {"returncode": result.returncode,
                "output": body[:MAX_OUTPUT_BYTES].decode("utf-8", errors="replace"),
                "truncated": truncated}
    except subprocess.TimeoutExpired as exc:
        body = (exc.stdout or b"")[:MAX_OUTPUT_BYTES]
        return {"returncode": None, "output": body.decode("utf-8", errors="replace"),
                "truncated": len(exc.stdout or b"") > MAX_OUTPUT_BYTES, "timed_out": True}
