from __future__ import annotations

from run_logger import get_log_file_path, initialize_run_log, traced


def test_initialize_run_log_resets_existing_content(tmp_path) -> None:
    log_dir = tmp_path / "log"
    log_dir.mkdir()
    existing_log = log_dir / "log_run.txt"
    existing_log.write_text("old content\n", encoding="utf-8")

    initialize_run_log(log_dir)

    content = existing_log.read_text(encoding="utf-8")
    assert "old content" not in content
    assert "Application run started" in content


def test_traced_decorator_logs_function_calls(tmp_path) -> None:
    initialize_run_log(tmp_path / "log")

    @traced
    def sample_function() -> str:
        return "ok"

    assert sample_function() == "ok"

    log_content = get_log_file_path().read_text(encoding="utf-8")
    assert "CALL tests.test_run_logger.sample_function" in log_content
    assert "RETURN tests.test_run_logger.sample_function" in log_content