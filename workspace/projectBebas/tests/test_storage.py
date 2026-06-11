"""
Unit tests for Task Manager storage.
"""

import unittest
import sys
import os
import tempfile
import json

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from task_manager.models import Task
from task_manager.storage import TaskStorage


class TestTaskStorage(unittest.TestCase):
    """Test cases for TaskStorage."""

    def setUp(self):
        """Create a temporary file for each test."""
        self.temp_file = tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False, encoding="utf-8"
        )
        self.temp_file.write("[]")
        self.temp_file.close()
        self.storage = TaskStorage(self.temp_file.name)

    def tearDown(self):
        """Clean up temporary file."""
        if os.path.exists(self.temp_file.name):
            os.unlink(self.temp_file.name)

    def test_get_all_empty(self):
        """Test getting all tasks from empty storage."""
        tasks = self.storage.get_all()
        self.assertEqual(tasks, [])

    def test_add_task(self):
        """Test adding a task."""
        task = Task(task_id=1, title="Test Task")
        self.storage.add(task)
        tasks = self.storage.get_all()
        self.assertEqual(len(tasks), 1)
        self.assertEqual(tasks[0].title, "Test Task")

    def test_get_by_id(self):
        """Test getting a task by ID."""
        task = Task(task_id=42, title="Find Me")
        self.storage.add(task)
        found = self.storage.get_by_id(42)
        self.assertIsNotNone(found)
        self.assertEqual(found.title, "Find Me")

    def test_get_by_id_not_found(self):
        """Test getting a non-existent task."""
        result = self.storage.get_by_id(999)
        self.assertIsNone(result)

    def test_update_task(self):
        """Test updating a task."""
        task = Task(task_id=1, title="Old Title")
        self.storage.add(task)
        updated = self.storage.update(1, title="New Title")
        self.assertIsNotNone(updated)
        self.assertEqual(updated.title, "New Title")

    def test_update_nonexistent_task(self):
        """Test updating a non-existent task."""
        result = self.storage.update(999, title="Ghost")
        self.assertIsNone(result)

    def test_delete_task(self):
        """Test deleting a task."""
        task = Task(task_id=1, title="To Delete")
        self.storage.add(task)
        result = self.storage.delete(1)
        self.assertTrue(result)
        self.assertEqual(self.storage.count(), 0)

    def test_delete_nonexistent_task(self):
        """Test deleting a non-existent task."""
        result = self.storage.delete(999)
        self.assertFalse(result)

    def test_get_next_id_empty(self):
        """Test next ID for empty storage."""
        self.assertEqual(self.storage.get_next_id(), 1)

    def test_get_next_id_with_tasks(self):
        """Test next ID with existing tasks."""
        self.storage.add(Task(task_id=1, title="First"))
        self.storage.add(Task(task_id=5, title="Fifth"))
        self.assertEqual(self.storage.get_next_id(), 6)

    def test_count(self):
        """Test counting tasks."""
        self.assertEqual(self.storage.count(), 0)
        self.storage.add(Task(task_id=1, title="One"))
        self.storage.add(Task(task_id=2, title="Two"))
        self.assertEqual(self.storage.count(), 2)

    def test_persistence(self):
        """Test that data persists across storage instances."""
        task = Task(task_id=1, title="Persistent")
        self.storage.add(task)

        # Create new storage instance with same file
        new_storage = TaskStorage(self.temp_file.name)
        tasks = new_storage.get_all()
        self.assertEqual(len(tasks), 1)
        self.assertEqual(tasks[0].title, "Persistent")


if __name__ == "__main__":
    unittest.main()
