from __future__ import annotations

import subprocess
import sys
import threading
from pathlib import Path

import pytest

import nautilus_7zip.runner as runner_module
from nautilus_7zip.commands import CommandSpec
from nautilus_7zip.runner import OperationHandle, RunResult, SubprocessRunner


def test_run_result_success_property() -> None:
    assert RunResult(0).succeeded
    assert not RunResult(1).succeeded
    assert not RunResult(0, cancelled=True).succeeded
    assert not RunResult(0, error="error").succeeded


def test_run_blocking_captures_output_progress_and_stdin(tmp_path: Path) -> None:
    password_file = tmp_path / "password.txt"
    script = (
        "import pathlib, sys; "
        f"pathlib.Path({str(password_file)!r}).write_text(sys.stdin.readline()); "
        "print(' 10% first'); print('100% done')"
    )
    output: list[str] = []
    progress: list[int] = []
    spec = CommandSpec((sys.executable, "-c", script), stdin_text="secret\n")

    result = SubprocessRunner().run_blocking(
        spec,
        on_output=output.append,
        on_progress=progress.append,
    )

    assert result.succeeded
    assert progress == [10, 100]
    assert "100% done" in "".join(output)
    assert password_file.read_text() == "secret\n"


def test_run_blocking_renders_terminal_backspaces_but_parses_raw_progress() -> None:
    script = (
        "import sys; "
        "sys.stdout.write(' 25%\\b\\b\\b\\b    \\b\\b\\b\\b+ source.txt\\n'); "
        "sys.stdout.flush()"
    )
    output: list[str] = []
    progress: list[int] = []

    result = SubprocessRunner().run_blocking(
        CommandSpec((sys.executable, "-c", script)),
        on_output=output.append,
        on_progress=progress.append,
    )

    assert result.succeeded
    assert output == ["+ source.txt\n"]
    assert progress == [25]


def test_run_blocking_reports_missing_executable() -> None:
    result = SubprocessRunner().run_blocking(CommandSpec(("/definitely/missing/7z",)))
    assert result.returncode == 127
    assert result.error


def test_asynchronous_runner_dispatches_callbacks() -> None:
    calls: list[tuple[str, object]] = []
    complete = threading.Event()

    def dispatcher(callback, *args):
        calls.append(("dispatch", callback))
        return callback(*args)

    def on_complete(result: RunResult) -> None:
        calls.append(("complete", result.returncode))
        complete.set()

    spec = CommandSpec((sys.executable, "-c", "print('25%')"))
    handle = SubprocessRunner(dispatcher).start(
        spec,
        on_output=lambda line: calls.append(("output", line)),
        on_progress=lambda value: calls.append(("progress", value)),
        on_complete=on_complete,
    )

    assert complete.wait(5)
    assert not handle.cancelled
    assert ("progress", 25) in calls
    assert ("complete", 0) in calls


def test_cancel_before_attach_terminates_process(monkeypatch: pytest.MonkeyPatch) -> None:
    terminated: list[object] = []
    monkeypatch.setattr(runner_module, "_terminate_process", terminated.append)
    process = object()
    handle = OperationHandle()
    handle.cancel()
    handle.attach(process)  # type: ignore[arg-type]
    assert handle.cancelled
    assert terminated == [process]


def test_cancel_after_attach_terminates_process(monkeypatch: pytest.MonkeyPatch) -> None:
    terminated: list[object] = []
    monkeypatch.setattr(runner_module, "_terminate_process", terminated.append)
    process = object()
    handle = OperationHandle()
    handle.attach(process)  # type: ignore[arg-type]
    handle.cancel()
    assert terminated == [process]


def test_terminate_ignores_finished_process() -> None:
    process = subprocess.Popen([sys.executable, "-c", "pass"], start_new_session=True, text=True)
    process.wait(timeout=5)
    runner_module._terminate_process(process)
    assert process.returncode == 0


def test_terminate_falls_back_when_process_group_signal_fails(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class FakeProcess:
        pid = 123
        terminated = False

        def poll(self):
            return None

        def terminate(self):
            self.terminated = True

    process = FakeProcess()
    monkeypatch.setattr(
        runner_module.os,
        "killpg",
        lambda *_args: (_ for _ in ()).throw(PermissionError),
    )
    runner_module._terminate_process(process)  # type: ignore[arg-type]
    assert process.terminated


def test_terminate_ignores_disappearing_fallback_process(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class FakeProcess:
        pid = 123

        def poll(self):
            return None

        def terminate(self):
            raise ProcessLookupError

    monkeypatch.setattr(
        runner_module.os,
        "killpg",
        lambda *_args: (_ for _ in ()).throw(ProcessLookupError),
    )
    runner_module._terminate_process(FakeProcess())  # type: ignore[arg-type]
