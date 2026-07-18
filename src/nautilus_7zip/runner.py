"""Asynchronous, cancellable execution of 7-Zip commands."""

from __future__ import annotations

import os
import signal
import subprocess
import threading
from collections.abc import Callable
from contextlib import suppress
from dataclasses import dataclass
from typing import Any

from .commands import CommandSpec
from .progress import parse_progress

OutputCallback = Callable[[str], None]
ProgressCallback = Callable[[int], None]
CompleteCallback = Callable[["RunResult"], None]
Dispatcher = Callable[..., Any]


@dataclass(frozen=True, slots=True)
class RunResult:
    returncode: int
    cancelled: bool = False
    error: str | None = None

    @property
    def succeeded(self) -> bool:
        return self.returncode == 0 and not self.cancelled and self.error is None


class OperationHandle:
    """Thread-safe cancellation handle returned to the UI."""

    def __init__(self) -> None:
        self._cancel_requested = threading.Event()
        self._lock = threading.Lock()
        self._process: subprocess.Popen[str] | None = None

    @property
    def cancelled(self) -> bool:
        return self._cancel_requested.is_set()

    def attach(self, process: subprocess.Popen[str]) -> None:
        with self._lock:
            self._process = process
            should_cancel = self._cancel_requested.is_set()
        if should_cancel:
            _terminate_process(process)

    def cancel(self) -> None:
        self._cancel_requested.set()
        with self._lock:
            process = self._process
        if process is not None:
            _terminate_process(process)


class SubprocessRunner:
    """Run commands on worker threads and dispatch callbacks to the UI loop."""

    def __init__(self, dispatcher: Dispatcher | None = None) -> None:
        self._dispatcher = dispatcher or _direct_dispatch

    def start(
        self,
        spec: CommandSpec,
        *,
        on_output: OutputCallback,
        on_progress: ProgressCallback,
        on_complete: CompleteCallback,
    ) -> OperationHandle:
        handle = OperationHandle()
        thread = threading.Thread(
            target=self._run,
            args=(spec, handle, on_output, on_progress, on_complete),
            daemon=True,
            name="nautilus-7zip-runner",
        )
        thread.start()
        return handle

    def run_blocking(
        self,
        spec: CommandSpec,
        *,
        handle: OperationHandle | None = None,
        on_output: OutputCallback | None = None,
        on_progress: ProgressCallback | None = None,
    ) -> RunResult:
        operation = handle or OperationHandle()
        output_callback = on_output or (lambda _line: None)
        progress_callback = on_progress or (lambda _percent: None)

        try:
            process = subprocess.Popen(
                spec.argv,
                stdin=subprocess.PIPE if spec.stdin_text is not None else subprocess.DEVNULL,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding="utf-8",
                errors="replace",
                bufsize=1,
                start_new_session=True,
            )
        except OSError as error:
            return RunResult(127, error=str(error))

        operation.attach(process)
        if spec.stdin_text is not None and process.stdin is not None:
            try:
                process.stdin.write(spec.stdin_text)
                process.stdin.flush()
            except BrokenPipeError:
                pass
            finally:
                process.stdin.close()

        if process.stdout is not None:
            for line in process.stdout:
                output_callback(line)
                percent = parse_progress(line)
                if percent is not None:
                    progress_callback(percent)

        returncode = process.wait()
        return RunResult(returncode, cancelled=operation.cancelled)

    def _run(
        self,
        spec: CommandSpec,
        handle: OperationHandle,
        on_output: OutputCallback,
        on_progress: ProgressCallback,
        on_complete: CompleteCallback,
    ) -> None:
        result = self.run_blocking(
            spec,
            handle=handle,
            on_output=lambda line: self._dispatcher(on_output, line),
            on_progress=lambda percent: self._dispatcher(on_progress, percent),
        )
        self._dispatcher(on_complete, result)


def _direct_dispatch(callback: Callable[..., Any], *args: Any) -> Any:
    return callback(*args)


def _terminate_process(process: subprocess.Popen[str]) -> None:
    if process.poll() is not None:
        return
    try:
        os.killpg(process.pid, signal.SIGTERM)
    except (ProcessLookupError, PermissionError):
        with suppress(ProcessLookupError):
            process.terminate()
