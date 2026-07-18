from __future__ import annotations

import os
import shutil
import stat
import subprocess
from collections.abc import Callable


class CloneError(RuntimeError):
    pass


def _clear_readonly_and_retry(func: Callable[[str], None], path: str, _exc: BaseException) -> None:
    os.chmod(path, stat.S_IWRITE)
    func(path)


def clone_repo(url: str, dest_dir: str, timeout_seconds: int, max_clone_mb: int) -> None:
    env = {**os.environ, "GIT_CONFIG_NOSYSTEM": "1", "GIT_TERMINAL_PROMPT": "0"}
    try:
        subprocess.run(
            ["git", "clone", "--no-checkout", "--depth", "1", "--", url, dest_dir],
            env=env,
            timeout=timeout_seconds,
            check=True,
            capture_output=True,
            text=True,
        )
        subprocess.run(
            ["git", "-C", dest_dir, "-c", "core.hooksPath=/dev/null", "checkout", "HEAD"],
            env=env,
            timeout=timeout_seconds,
            check=True,
            capture_output=True,
            text=True,
        )
    except subprocess.TimeoutExpired as exc:
        raise CloneError(f"Clone timed out after {timeout_seconds}s") from exc
    except subprocess.CalledProcessError as exc:
        raise CloneError(f"git clone failed: {exc.stderr.strip()}") from exc

    shutil.rmtree(os.path.join(dest_dir, ".git"), onexc=_clear_readonly_and_retry)

    total_size = sum(
        os.path.getsize(os.path.join(dirpath, f))
        for dirpath, _dirnames, filenames in os.walk(dest_dir)
        for f in filenames
    )
    if total_size > max_clone_mb * 1024 * 1024:
        raise CloneError(f"Cloned repository exceeds size limit ({total_size / 1024 / 1024:.1f}MB > {max_clone_mb}MB)")
