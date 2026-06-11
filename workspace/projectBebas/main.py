#!/usr/bin/env python3
"""
Task Manager CLI - Main Entry Point
A simple terminal-based task management application.

Usage:
    python main.py              # Interactive mode
    python main.py --help       # Show help
    python main.py --version    # Show version
"""

import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from task_manager import __version__
from task_manager.models import Task
from task_manager.storage import TaskStorage
from task_manager.display import Display
from task_manager.utils import get_input, get_choice, confirm_action, export_to_csv

# Default data file path
DATA_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "tasks.json")


class TaskManagerApp:
    """Main application class for Task Manager CLI."""

    def __init__(self, data_file=DATA_FILE):
        self.storage = TaskStorage(data_file)
        self.running = True

    def run(self):
        """Main application loop."""
        Display.show_banner()

        while self.running:
            Display.show_menu()
            choice = get_input("Pilih menu (1-9)")

            actions = {
                "1": self.view_all_tasks,
                "2": self.add_task,
                "3": self.edit_task,
                "4": self.delete_task,
                "5": self.search_tasks,
                "6": self.view_stats,
                "7": self.change_status,
                "8": self.export_tasks,
                "9": self.exit_app,
            }

            action = actions.get(choice)
            if action:
                action()
            else:
                Display.show_error("Pilihan tidak valid! Masukkan angka 1-9.")

    def view_all_tasks(self):
        """Display all tasks."""
        tasks = self.storage.get_all()
        Display.show_tasks(tasks)

    def add_task(self):
        """Add a new task."""
        print("\n  ═══ ➕ TAMBAH TUGAS BARU ═══\n")

        task_id = self.storage.get_next_id()
        title = get_input("Judul tugas", required=True)
        description = get_input("Deskripsi (opsional)")

        print(f"\n  Prioritas: {Task.LOW} / {Task.MEDIUM} / {Task.HIGH}")
        priority = get_choice("Pilih prioritas", Task.PRIORITIES)

        task = Task(task_id=task_id, title=title, description=description, priority=priority)
        self.storage.add(task)

        Display.show_success(f"Tugas '{title}' berhasil ditambahkan dengan ID {task_id}!")

    def edit_task(self):
        """Edit an existing task."""
        print("\n  ═══ ✏️  EDIT TUGAS ═══\n")

        task_id = get_input("Masukkan ID tugas yang akan diedit", required=True)
        try:
            task_id = int(task_id)
        except ValueError:
            Display.show_error("ID harus berupa angka!")
            return

        task = self.storage.get_by_id(task_id)
        if not task:
            Display.show_error(f"Tugas dengan ID {task_id} tidak ditemukan!")
            return

        Display.show_task(task)

        print("  (Tekan Enter untuk mempertahankan nilai lama)\n")
        new_title = get_input(f"Judul baru", default=task.title)
        new_desc = get_input(f"Deskripsi baru", default=task.description)

        print(f"\n  Prioritas saat ini: {task.priority}")
        print(f"  Pilihan: {Task.LOW} / {Task.MEDIUM} / {Task.HIGH}")
        new_priority = get_input(f"Prioritas baru (atau Enter untuk tetap)", default=task.priority)

        if new_priority not in Task.PRIORITIES:
            new_priority = task.priority

        self.storage.update(task_id, title=new_title, description=new_desc, priority=new_priority)
        Display.show_success(f"Tugas ID {task_id} berhasil diperbarui!")

    def delete_task(self):
        """Delete a task."""
        print("\n  ═══ 🗑️  HAPUS TUGAS ═══\n")

        task_id = get_input("Masukkan ID tugas yang akan dihapus", required=True)
        try:
            task_id = int(task_id)
        except ValueError:
            Display.show_error("ID harus berupa angka!")
            return

        task = self.storage.get_by_id(task_id)
        if not task:
            Display.show_error(f"Tugas dengan ID {task_id} tidak ditemukan!")
            return

        Display.show_task(task)

        if confirm_action("Yakin ingin menghapus tugas ini?"):
            self.storage.delete(task_id)
            Display.show_success(f"Tugas ID {task_id} berhasil dihapus!")
        else:
            Display.show_info("Penghapusan dibatalkan.")

    def search_tasks(self):
        """Search tasks by keyword."""
        print("\n  ═══ 🔍 CARI TUGAS ═══\n")

        keyword = get_input("Masukkan kata kunci", required=True)
        tasks = self.storage.get_all()

        results = [
            t for t in tasks
            if keyword.lower() in t.title.lower()
            or keyword.lower() in t.description.lower()
            or keyword.lower() in t.priority.lower()
            or keyword.lower() in t.status.lower()
        ]

        Display.show_search_results(results, keyword)

    def view_stats(self):
        """Display task statistics."""
        tasks = self.storage.get_all()
        Display.show_stats(tasks)

    def change_status(self):
        """Change the status of a task."""
        print("\n  ═══ 🔄 UBAH STATUS TUGAS ═══\n")

        task_id = get_input("Masukkan ID tugas", required=True)
        try:
            task_id = int(task_id)
        except ValueError:
            Display.show_error("ID harus berupa angka!")
            return

        task = self.storage.get_by_id(task_id)
        if not task:
            Display.show_error(f"Tugas dengan ID {task_id} tidak ditemukan!")
            return

        Display.show_task(task)

        print(f"  Status tersedia: {Task.TODO} / {Task.IN_PROGRESS} / {Task.DONE}")
        new_status = get_choice("Pilih status baru", Task.STATUSES)

        self.storage.update(task_id, status=new_status)
        Display.show_success(f"Status tugas ID {task_id} diubah menjadi '{new_status}'!")

    def export_tasks(self):
        """Export tasks to CSV."""
        print("\n  ═══ 💾 EXPORT KE CSV ═══\n")

        tasks = self.storage.get_all()
        if not tasks:
            Display.show_info("Tidak ada tugas untuk di-export.")
            return

        default_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "tasks_export.csv")
        filepath = get_input(f"Path file CSV", default=default_path)

        success, message = export_to_csv(tasks, filepath)
        if success:
            Display.show_success(message)
        else:
            Display.show_error(message)

    def exit_app(self):
        """Exit the application."""
        if confirm_action("Yakin ingin keluar?"):
            print("\n  🐢 Terima kasih telah menggunakan Task Manager CLI!\n")
            self.running = False
        else:
            Display.show_info("Kembali ke menu utama.")


def main():
    """Entry point."""
    if len(sys.argv) > 1:
        arg = sys.argv[1].lower()
        if arg in ("--version", "-v"):
            print(f"Task Manager CLI v{__version__}")
            return
        elif arg in ("--help", "-h"):
            print(__doc__)
            return
        else:
            print(f"Unknown argument: {sys.argv[1]}")
            print("Usage: python main.py [--help | --version]")
            return

    app = TaskManagerApp()
    app.run()


if __name__ == "__main__":
    main()
