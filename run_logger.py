from __future__ import annotations

from datetime import datetime
from functools import wraps
from pathlib import Path
from typing import Callable, ParamSpec, TypeVar


P = ParamSpec("P")
R = TypeVar("R")

PROJECT_ROOT = Path(__file__).resolve().parent
DEFAULT_LOG_DIR = PROJECT_ROOT / "log"
DEFAULT_LOG_FILE = DEFAULT_LOG_DIR / "log_run.txt"

_active_log_file = DEFAULT_LOG_FILE


def get_log_file_path() -> Path:
    """Return the current run log file path."""
    return _active_log_file


def _ensure_log_file() -> None:
    """Create the log directory and file if needed."""
    _active_log_file.parent.mkdir(parents=True, exist_ok=True)
    if not _active_log_file.exists():
        _active_log_file.write_text("", encoding="utf-8")


def _append_line(line: str) -> None:
    """Append one line to the active log file."""
    _ensure_log_file()
    with _active_log_file.open("a", encoding="utf-8") as log_file:
        log_file.write(f"{line}\n")


def initialize_run_log(log_dir: Path | str | None = None) -> Path:
    """Reset the per-run log file at application startup."""
    global _active_log_file

    target_dir = Path(log_dir) if log_dir is not None else DEFAULT_LOG_DIR
    target_dir.mkdir(parents=True, exist_ok=True)
    _active_log_file = target_dir / "log_run.txt"
    _active_log_file.write_text("", encoding="utf-8")
    _append_line(f"=== Application run started at {datetime.now().isoformat()} ===")
    return _active_log_file


def log_event(message: str) -> None:
    """Write a timestamped event message to the run log."""
    timestamp = datetime.now().isoformat(timespec="seconds")
    _append_line(f"[{timestamp}] {message}")


def traced(func: Callable[P, R]) -> Callable[P, R]:
    """Decorator that logs function calls, returns, and raised exceptions."""
    qualified_name = f"{func.__module__}.{func.__name__}"

    @wraps(func)
    def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
        log_event(f"CALL {qualified_name}")
        try:
            result = func(*args, **kwargs)
            log_event(f"RETURN {qualified_name}")
            return result
        except Exception as exc:
            log_event(
                f"ERROR {qualified_name}: {exc.__class__.__name__}: {exc}"
            )
            raise

    return wrapper