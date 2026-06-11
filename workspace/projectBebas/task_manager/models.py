"""
Data models for Task Manager.
"""

import json
from datetime import datetime


class Task:
    """Represents a single task."""

    LOW = "rendah"
    MEDIUM = "sedang"
    HIGH = "tinggi"
    PRIORITIES = [LOW, MEDIUM, HIGH]

    TODO = "todo"
    IN_PROGRESS = "dikerjakan"
    DONE = "selesai"
    STATUSES = [TODO, IN_PROGRESS, DONE]

    def __init__(self, task_id, title, description="", priority=LOW, status=TODO, created_at=None, updated_at=None):
        self.id = task_id
        self.title = title
        self.description = description
        self.priority = priority if priority in self.PRIORITIES else self.LOW
        self.status = status if status in self.STATUSES else self.TODO
        self.created_at = created_at or datetime.now().isoformat()
        self.updated_at = updated_at or datetime.now().isoformat()

    def to_dict(self):
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "priority": self.priority,
            "status": self.status,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    @classmethod
    def from_dict(cls, data):
        return cls(
            task_id=data["id"],
            title=data["title"],
            description=data.get("description", ""),
            priority=data.get("priority", cls.LOW),
            status=data.get("status", cls.TODO),
            created_at=data.get("created_at"),
            updated_at=data.get("updated_at"),
        )

    def __str__(self):
        priority_icon = {"rendah": "🟢", "sedang": "🟡", "tinggi": "🔴"}
        status_icon = {"todo": "📋", "dikerjakan": "⏳", "selesai": "✅"}
        return (
            f"  [{self.id}] {status_icon.get(self.status, '📋')} {self.title}\n"
            f"       Prioritas: {priority_icon.get(self.priority, '🟢')} {self.priority}\n"
            f"       Status: {self.status}\n"
            f"       Deskripsi: {self.description or '(kosong)'}\n"
            f"       Dibuat: {self.created_at[:19]}\n"
            f"       Diupdate: {self.updated_at[:19]}"
        )
