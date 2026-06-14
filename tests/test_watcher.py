"""FileWatcher start/stop and event filtering.

NB: FileWatcher.start() blocks on a `while self.running: time.sleep(0.1)` loop.
For tests we always run start() in a background thread so we can call stop() to
unblock it. Phase 1.2 (multi-watcher pool) should also rework this loop to
something async-friendly so the API server's create_task pattern stops being a
landmine.
"""
import threading
import time
from pathlib import Path
from threading import Event

import pytest

from src.visualization.core.watcher import CodeFileHandler, FileWatcher


def _start_in_thread(watcher: FileWatcher) -> threading.Thread:
    thread = threading.Thread(target=watcher.start, daemon=True)
    thread.start()
    for _ in range(50):
        if watcher.running:
            break
        time.sleep(0.05)
    return thread


def test_handler_filters_to_code_extensions(tmp_path: Path) -> None:
    received: list[list[str]] = []
    handler = CodeFileHandler(callback=received.append, debounce_seconds=0.05)

    class _Event:
        def __init__(self, path: str, is_directory: bool = False) -> None:
            self.src_path = path
            self.is_directory = is_directory
            self.event_type = "modified"

    handler.on_any_event(_Event(str(tmp_path / "a.py")))
    handler.on_any_event(_Event(str(tmp_path / "b.txt")))
    handler.on_any_event(_Event(str(tmp_path / "node_modules" / "x.js")))

    assert str(tmp_path / "a.py") in handler.pending_changes
    assert str(tmp_path / "b.txt") not in handler.pending_changes
    assert not any("node_modules" in p for p in handler.pending_changes)


def test_handler_ignores_directory_events(tmp_path: Path) -> None:
    handler = CodeFileHandler(callback=lambda _changes: None, debounce_seconds=0.05)

    class _DirEvent:
        src_path = str(tmp_path)
        is_directory = True
        event_type = "created"

    handler.on_any_event(_DirEvent())
    assert handler.pending_changes == set()


def test_handler_process_pending_respects_debounce(tmp_path: Path) -> None:
    fired: list[list[str]] = []
    handler = CodeFileHandler(callback=fired.append, debounce_seconds=0.2)

    class _Event:
        def __init__(self, path: str) -> None:
            self.src_path = path
            self.is_directory = False
            self.event_type = "modified"

    handler.on_any_event(_Event(str(tmp_path / "a.py")))
    handler.process_pending()
    assert fired == []  # still inside debounce window

    time.sleep(0.25)
    handler.process_pending()
    assert len(fired) == 1
    assert handler.pending_changes == set()


def test_filewatcher_start_stop(tmp_path: Path) -> None:
    watcher = FileWatcher(
        str(tmp_path),
        callback=lambda _changes: None,
        debounce_seconds=0.1,
    )
    thread = _start_in_thread(watcher)
    try:
        assert watcher.running is True
        assert watcher.observer.is_alive()
    finally:
        watcher.stop()
        thread.join(timeout=3)
    assert not thread.is_alive()
    assert not watcher.observer.is_alive()


def test_filewatcher_invokes_callback_on_change(tmp_path: Path) -> None:
    fired = Event()
    seen: list[str] = []

    def on_change(changes: list[str]) -> None:
        seen.extend(changes)
        fired.set()

    watcher = FileWatcher(str(tmp_path), callback=on_change, debounce_seconds=0.1)
    thread = _start_in_thread(watcher)
    try:
        target = tmp_path / "fresh.py"
        target.write_text("print('hi')\n", encoding="utf-8")
        for i in range(40):
            if fired.wait(timeout=0.1):
                break
            target.write_text(f"print('hi {i}')\n", encoding="utf-8")
        assert fired.is_set(), "watcher callback was never invoked"
        assert any("fresh.py" in p for p in seen)
    finally:
        watcher.stop()
        thread.join(timeout=3)


def test_filewatcher_rejects_missing_path(tmp_path: Path) -> None:
    with pytest.raises(ValueError):
        FileWatcher(str(tmp_path / "nope"), callback=lambda _c: None)
