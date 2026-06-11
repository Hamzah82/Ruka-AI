
"""
Display and formatting utilities for Task Manager CLI.
"""

from .models import Task


class Display:
    """Handles all visual output for the task manager."""

    BANNER = r"""
  ╔══════════════════════════════════════════╗
  ║     🐢 TASK MANAGER CLI v1.0            ║
  ║     Dibuat oleh Ruka AI                 ║
  ╚══════════════════════════════════════════╝
    """

    MENU = """
  ┌──────────────────────────────────────────┐
  │              📌 MENU UTAMA               │
  ├──────────────────────────────────────────┤
  │  1. 📋 Lihat semua tugas                 │
  │  2. ➕ Tambah tugas baru                 │
  │  3. ✏️  Edit tugas                       │
  │  4. 🗑️  Hapus tugas                      │
  │  5. 🔍 Cari tugas                        │
  │  6. 📊 Lihat statistik                   │
  │  7. 🔄 Ubah status tugas                 │
  │  8. 💾 Export tugas ke CSV               │
  │  9. ❌ Keluar                             │
  └──────────────────────────────────────────┘
    """

    @staticmethod
    def show_banner():
        print(Display.BANNER)

    @staticmethod
    def show_menu():
        print(Display.MENU)

    @staticmethod
    def show_tasks(tasks):
        """Display a list of tasks."""
        if not tasks:
            print("\n  📭 Belum ada tugas. Tambahkan tugas baru!\n")
            return

        print(f"\n  ═══ 📋 DAFTAR TUGAS ({len(tasks)} total) ═══\n")
        for task in tasks:
            print(task)
            print()

    @staticmethod
    def show_task(task):
        """Display a single task."""
        if task:
            print(f"\n  ═══ DETAIL TUGAS ═══\n{task}\n")
        else:
            print("\n  ❌ Tugas tidak ditemukan.\n")

    @staticmethod
    def show_stats(tasks):
        """Display task statistics."""
        total = len(tasks)
        todo = sum(1 for t in tasks if t.status == Task.TODO)
        in_progress = sum(1 for t in tasks if t.status == Task.IN_PROGRESS)
        done = sum(1 for t in tasks if t.status == Task.Done)
        high = sum(1 for t in tasks if t.priority == Task.HIGH)
        medium = sum(1 for t in tasks if t.priority == Task.MEDIUM)
        low = sum(1 for t in tasks if t.priority == Task.LOW)

        print(f"""
  ═══ 📊 STATISTIK TUGAS ═══

  Total tugas    : {total}
  ─────────────────────────
  📋 Todo        : {todo}
  ⏳ Dikerjakan   : {in_progress}
  ✅ Selesai      : {done}
  ─────────────────────────
  🔴 Prioritas tinggi  : {high}
  🟡 Prioritas sedang  : {medium}
  🟢 Prioritas rendah  : {low}
        """)

    @staticmethod
    def show_success(message):
        print(f"\n  ✅ {message}\n")

    @staticmethod
    def show_error(message):
        print(f"\n  ❌ {message}\n")

    @staticmethod
    def show_info(message):
        print(f"\n  ℹ️  {message}\n")

    @staticmethod
    def show_search_results(tasks, keyword):
        """Display search results."""
        if not tasks:
            print(f"\n  🔍 Tidak ada tugas yang cocok dengan '{keyword}'.\n")
            return
        print(f"\n  ═══ HASIL PENCARIAN: '{keyword}' ({len(tasks)} ditemukan) ═══\n")
        for task in tasks:
            print(task)
            print()
