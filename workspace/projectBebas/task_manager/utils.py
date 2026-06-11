
"""
Utility functions for Task Manager CLI.
"""

import csv
import os
from datetime import datetime


def get_input(prompt, required=False, default=None):
    """Get user input with optional default value."""
    if default:
        full_prompt = f"  {prompt} [{default}]: "
    else:
        full_prompt = f"  {prompt}: "

    while True:
        value = input(full_prompt).strip()
        if value:
            return value
        if default is not None:
            return default
        if not required:
            return ""
        print("  ⚠️  Input wajib diisi!")


def get_choice(prompt, valid_choices):
    """Get a valid choice from user."""
    while True:
        value = input(f"  {prompt}: ").strip().lower()
        if value in valid_choices:
            return value
        print(f"  ⚠️  Pilihan tidak valid. Pilihan: {', '.join(valid_choices)}")


def confirm_action(prompt="Apakah Anda yakin?"):
    """Ask for confirmation."""
    value = input(f"  {prompt} (y/n): ").strip().lower()
    return value in ("y", "ya", "yes")


def export_to_csv(tasks, filepath):
    """Export tasks to a CSV file."""
    if not tasks:
        return False, "Tidak ada tugas untuk di-export."

    try:
        with open(filepath, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["ID", "Judul", "Deskripsi", "Prioritas", "Status", "Dibuat", "Diupdate"])
            for task in tasks:
                writer.writerow([
                    task.id,
                    task.title,
                    task.description,
                    task.priority,
                    task.status,
                    task.created_at[:19],
                    task.updated_at[:19],
                ])
        return True, f"Berhasil export {len(tasks)} tugas ke '{filepath}'."
    except Exception as e:
        return False, f"Gagal export: {str(e)}"


def format_date(iso_string):
    """Format ISO date string to readable format."""
    try:
        dt = datetime.fromisoformat(iso_string)
        return dt.strftime("%d %B %Y, %H:%M")
    except (ValueError, TypeError):
        return iso_string


def clear_screen():
    """Clear the terminal screen."""
    os.system("cls" if os.name == "nt" else "clear")
