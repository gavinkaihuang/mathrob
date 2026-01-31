import time
import os
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import threading
import asyncio

class ScanHandler(FileSystemEventHandler):
    def __init__(self, callback):
        self.callback = callback

    def on_created(self, event):
        if not event.is_directory and event.src_path.lower().endswith(('.jpg', '.jpeg', '.png')):
            print(f"New scan detected: {event.src_path}")
            # Run callback in a thread-safe way or simply call it
            # For async callback, we might need a loop
            if self.callback:
                 self.callback(event.src_path)

class FileWatcher:
    def __init__(self, watch_dir: str, callback):
        self.watch_dir = watch_dir
        self.callback = callback
        self.observer = Observer()
        
        # Ensure directory exists
        if not os.path.exists(watch_dir):
            os.makedirs(watch_dir)

    def start(self):
        event_handler = ScanHandler(self.callback)
        self.observer.schedule(event_handler, self.watch_dir, recursive=False)
        self.observer.start()
        print(f"Started watching directory: {self.watch_dir}")

    def stop(self):
        self.observer.stop()
        self.observer.join()
