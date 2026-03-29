# filesystem_watcher.py
from watchdog.observers.polling import PollingObserver
from watchdog.events import FileSystemEventHandler
from pathlib import Path
import shutil
import time
import logging
from watchers.base_watcher import BaseWatcher
from utils.audit_logger import audit_log

class DropFolderHandler(FileSystemEventHandler):
    def __init__(self, vault_path: str):
        self.needs_action = Path(vault_path) / 'Needs_Action'
        self.inbox = Path(vault_path) / 'Inbox'
        self.logger = logging.getLogger(self.__class__.__name__)

    def on_created(self, event):
        if event.is_directory:
            return
        source = Path(event.src_path)
        # Only process files dropped in the Inbox folder
        if self.inbox in source.parents:
            # Create a metadata file instead of copying the original
            self.create_metadata(source)
            self.logger.info(f'New file detected: {source.name}')

    def on_modified(self, event):
        if event.is_directory:
            return
        source = Path(event.src_path)
        # Only process files modified in the Inbox folder
        if self.inbox in source.parents:
            # Only create metadata if file is "stable" (not being written to)
            time.sleep(1)  # Brief delay to ensure file is completely written
            self.create_metadata(source)
            self.logger.info(f'Modified file detected: {source.name}')

    def create_metadata(self, source: Path):
        # Create a markdown file with metadata about the dropped file
        import datetime
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        meta_filename = f"FILE_{timestamp}_{source.name}.md"
        meta_path = self.needs_action / meta_filename

        # Read file content if it's a text file (limit size to avoid issues)
        file_content = ""
        try:
            if source.stat().st_size < 10000:  # Only read files less than 10KB
                with open(source, 'r', encoding='utf-8', errors='ignore') as f:
                    file_content = f.read(500)  # First 500 chars
        except:
            file_content = "[Non-text file or could not read content]"

        meta_content = f"""---
type: file_drop
original_name: {source.name}
size: {source.stat().st_size}
timestamp: {datetime.datetime.now().isoformat()}
status: pending
---

# File Drop for Processing

## Original File
- **Name:** {source.name}
- **Size:** {source.stat().st_size} bytes
- **Detected:** {datetime.datetime.now().isoformat()}

## File Content Preview
```
{file_content}
```

## Suggested Actions
- [ ] Review file content
- [ ] Determine appropriate processing
- [ ] Move processed file to Done folder
"""
        meta_path.write_text(meta_content)
        self.logger.info(f'Created action file: {meta_path.name}')
        audit_log(
            action_type='file_detected',
            actor='filesystem_watcher',
            target=source.name,
            parameters={'size': source.stat().st_size, 'action_file': meta_path.name},
            result='success',
        )


class FileSystemWatcher(BaseWatcher):
    def __init__(self, vault_path: str, watch_folder: str = None):
        super().__init__(vault_path)
        self.watch_folder = Path(watch_folder) if watch_folder else self.vault_path / 'Inbox'
        self.observer = PollingObserver(timeout=5)
        self.handler = DropFolderHandler(self.vault_path)

    def check_for_updates(self) -> list:
        # This is not used for file system watcher since it uses event handling
        return []

    def create_action_file(self, item) -> Path:
        # This is not used for file system watcher since it uses event handling
        pass

    def run(self):
        # Set up the file system observer
        self.observer.schedule(self.handler, str(self.watch_folder), recursive=True)
        self.observer.start()
        self.logger.info(f'Starting FileSystemWatcher for {self.watch_folder}')

        try:
            while True:
                time.sleep(1)  # Keep the main thread alive
        except KeyboardInterrupt:
            self.observer.stop()
            self.logger.info('FileSystemWatcher stopped by user')
        finally:
            self.observer.join()