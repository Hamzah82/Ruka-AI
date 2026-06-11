"""
Unit tests for Task Manager models.
"""

import unittest
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from task_manager.models import Task


class TestTask(unittest.TestCase):
    """Test cases for the Task model."""

    def test_create_task(self):
        """Test creating a basic task."""
        task = Task(task_id=1, title="Belajar Python")
        self.assertEqual(task.id, 1)
        self.assertEqual(task.title, "Belajar Python")
        self.assertEqual(task.priority, Task.LOW)
        self.assertEqual(task.status, Task.TODO)
        self.assertEqual(task.description, "")

    def test_create_task_with_all_fields(self):
        """Test creating a task with all fields."""
        task = Task(
            task_id=2,
            title="Selesaikan project",
            description="Selesaikan project akhir",
            priority=Task.HIGH,
            status=Task.IN_PROGRESS,
        )
        self.assertEqual(task.id, 2)
        self.assertEqual(task.title, "Selesaikan project")
        self.assertEqual(task.description, "Selesaikan project akhir")
        self.assertEqual(task.priority, Task.HIGH)
        self.assertEqual(task.status, Task.IN_PROGRESS)

    def test_to_dict(self):
        """Test converting task to dictionary."""
        task = Task(task_id=1, title="Test", description="Desc")
        data = task.to_dict()
        self.assertIsInstance(data, dict)
        self.assertEqual(data["id"], 1)
        self.assertEqual(data["title"], "Test")
        self.assertEqual(data["description"], "Desc")
        self.assertIn("created_at", data)
        self.assertIn("updated_at", data)

    def test_from_dict(self):
        """Test creating task from dictionary."""
        data = {
            "id": 5,
            "title": "From Dict",
            "description": "Test from dict",
            "priority": Task.HIGH,
            "status": Task.DONE,
            "created_at": "2025-01-01T00:00:00",
            "updated_at": "2025-01-02T00:00:00",
        }
        task = Task.from_dict(data)
        self.assertEqual(task.id, 5)
        self.assertEqual(task.title, "From Dict")
        self.assertEqual(task.priority, Task.HIGH)
        self.assertEqual(task.status, Task.DONE)

    def test_invalid_priority_defaults_to_low(self):
        """Test that invalid priority defaults to LOW."""
        task = Task(task_id=1, title="Test", priority="invalid")
        self.assertEqual(task.priority, Task.LOW)

    def test_invalid_status_defaults_to_todo(self):
        """Test that invalid status defaults to TODO."""
        task = Task(task_id=1, title="Test", status="invalid")
        self.assertEqual(task.status, Task.TODO)

    def test_str_representation(self):
        """Test string representation of a task."""
        task = Task(task_id=1, title="Test Task")
        result = str(task)
        self.assertIn("Test Task", result)
        self.assertIn("1", result)

    def test_priorities_list(self):
        """Test that priorities list is correct."""
        self.assertEqual(Task.PRIORITIES, ["rendah", "sedang", "tinggi"])

    def test_statuses_list(self):
        """Test that statuses list is correct."""
        self.assertEqual(Task.STATUSES, ["todo", "dikerjakan", "selesai"])


if __name__ == "__main__":
    unittest.main()
