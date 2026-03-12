# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2024 Chris Arseno / GozerAI

"""
File system watcher for real-time code analysis.

Monitors file changes and triggers incremental re-analysis.
"""

import logging
from pathlib import Path
from typing import Callable, Set, List
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler, FileSystemEvent
import time

logger = logging.getLogger(__name__)


class CodeFileHandler(FileSystemEventHandler):
    """
    Handle file system events for code files.
    
    Filters for relevant file types and batches changes
    before triggering callbacks.
    """
    
    CODE_EXTENSIONS = {'.py', '.js', '.jsx', '.ts', '.tsx'}
    IGNORE_PATTERNS = {'__pycache__', 'node_modules', '.git', 'dist', 'build'}
    
    def __init__(self, callback: Callable[[List[str]], None], debounce_seconds: float = 1.0):
        """
        Initialize file handler.
        
        Args:
            callback: Function to call with list of changed file paths
            debounce_seconds: Time to wait before processing changes (batching)
        """
        self.callback = callback
        self.debounce_seconds = debounce_seconds
        self.pending_changes: Set[str] = set()
        self.last_change_time: float = 0
    
    def on_any_event(self, event: FileSystemEvent) -> None:
        """Handle any file system event"""
        # Ignore directory events
        if event.is_directory:
            return
        
        # Get the file path
        file_path = Path(event.src_path)
        
        # Check if it's a code file we care about
        if not self._should_process(file_path):
            return
        
        # Add to pending changes
        self.pending_changes.add(str(file_path))
        self.last_change_time = time.time()
        
        logger.debug(f"File change detected: {file_path}")
    
    def _should_process(self, file_path: Path) -> bool:
        """Check if file should be processed"""
        # Check extension
        if file_path.suffix not in self.CODE_EXTENSIONS:
            return False
        
        # Check for ignored patterns
        path_str = str(file_path)
        for pattern in self.IGNORE_PATTERNS:
            if pattern in path_str:
                return False
        
        return True
    
    def process_pending(self) -> None:
        """Process pending changes if debounce period has elapsed"""
        if not self.pending_changes:
            return
        
        # Check if debounce period has elapsed
        if time.time() - self.last_change_time < self.debounce_seconds:
            return
        
        # Process changes
        changed_files = list(self.pending_changes)
        self.pending_changes.clear()
        
        logger.info(f"Processing {len(changed_files)} file changes")
        
        try:
            self.callback(changed_files)
        except Exception as e:
            logger.error(f"Error in change callback: {e}", exc_info=True)


class FileWatcher:
    """
    Watch a directory for code file changes.
    
    Monitors file system for changes and triggers re-analysis
    with debouncing to handle rapid successive changes.
    """
    
    def __init__(
        self,
        path: str,
        callback: Callable[[List[str]], None],
        debounce_seconds: float = 1.0,
    ):
        """
        Initialize file watcher.
        
        Args:
            path: Directory to watch
            callback: Function to call when files change
            debounce_seconds: Time to wait before processing changes
        """
        self.path = Path(path).resolve()
        self.callback = callback
        self.debounce_seconds = debounce_seconds
        
        if not self.path.exists():
            raise ValueError(f"Path does not exist: {path}")
        
        self.observer = Observer()
        self.handler = CodeFileHandler(callback, debounce_seconds)
        self.running = False
        
        logger.info(f"Initialized file watcher for {self.path}")
    
    def start(self) -> None:
        """Start watching for file changes"""
        if self.running:
            logger.warning("Watcher already running")
            return
        
        # Schedule the observer
        self.observer.schedule(
            self.handler,
            str(self.path),
            recursive=True,
        )
        
        # Start the observer
        self.observer.start()
        self.running = True
        
        logger.info(f"File watcher started for {self.path}")
        
        # Run processing loop
        try:
            while self.running:
                time.sleep(0.1)  # Check every 100ms
                self.handler.process_pending()
        except KeyboardInterrupt:
            self.stop()
    
    def stop(self) -> None:
        """Stop watching for file changes"""
        if not self.running:
            return
        
        self.running = False
        self.observer.stop()
        self.observer.join()
        
        logger.info("File watcher stopped")
    
    def __enter__(self):
        """Context manager entry"""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.stop()
