
"""
JSON file-based storage for Task Manager.
"""

import json
import os
from .models import Task


class TaskStorage:
    """Handles reading and writing tasks to a JSON file."""

    def __init__(self, filepath):
        self.filepath = filepath
        self._ensure_file_exists()

    def _ensure_file_exists(self):
        """Create the data file if it doesn't exist."""
        if not os.path.exists(self.filepath):
            directory = os.path.dirname(self.filepath)
            if directory and not os.path.exists(directory):
                os.makedirs(directory, exist_ok=True)
            self._write_all([])

    def _read_all(self):
        """Read all tasks from file."""
        try:
            with open(self.filepath, "r", encoding="utf-8") as f:
                data = json.load(f)
            return [Task.from_dict(item) for item in data]
        except (json.JSONDecodeError, FileNotFoundError):
            return []

    def _write_all(self, tasks):
        """Write all tasks to file."""
        with open(self.filepath, "w", encoding="utf-8") as f:
            json.dump([task.to_dict() for task in tasks], f, ensure_ascii=False, indent=2)

    def get_all(self):
        """Return all tasks."""
        return self._read_all()

    def get_by_id(self, task_id):
        """Return a task by its ID, or None."""
        tasks = self._read_all()
        for task in tasks:
            if task.id == task_id:
                return task
        return None

    def add(self, task):
        """Add a new task."""
        tasks = self._read_all()
        tasks.append(task)
        self._write_all(tasks)

    def update(self, task_id, **kwargs):
        """Update a task's fields."""
        tasks = self._read_all()
        for task in tasks:
            if task.id == task_id:
                for key, value in kwargs.items():
                    if hasattr(task, key) and value is not None:
                        setattr(task, key, value)
                from datetime import datetime
                task.updated_at = datetime.now().isoformat()
                self._write_all(tasks)
                return task
        return None

    def delete(self, task_id):
        """Delete a task by its ID."""
        tasks = self._read_all()
        filtered = [t for t in tasks if t.id != task_id]
        if len(filtered) < len(tasks):
            self._write_all(filtered)
            return True
        return False

    def get_next_id(self):
        """Get the next available task ID."""
        tasks = self._read_all()
        if not tasks:
            return 1
        return max(t.id for t in tasks) + 1

    def count(self):
        """Return total number of tasks."""
        return len(self._read_all())
