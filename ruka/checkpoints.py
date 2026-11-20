"""Checkpoint & undo untuk perubahan file di workspace.

Sebelum tool yang mengubah file dijalankan, isi file lama disalin ke
``<workspace>/.ruka/checkpoints/<grup>/`` beserta manifest JSON. ``/undo``
memulihkan grup terakhir, sehingga kesalahan agent (atau patch yang salah)
tidak langsung merusak pekerjaan user.

Desain:
- Satu grup = satu pemanggilan tool yang mengubah file.
- Snapshot hanya file yang benar-benar disentuh (plus isi folder untuk
  ``delete_folder``) — bukan seluruh workspace.
- File > 5 MB dilewati dan dicatat di manifest agar tidak menghabiskan disk.
- Grup lama dipangkas otomatis (default 30 grup terakhir).
"""
from __future__ import annotations

import json
import os
import shutil
import time
import uuid

MAX_FILE_BYTES = 5 * 1024 * 1024
MAX_ENTRIES = 500
KEEP_GROUPS = 30
CHECKPOINT_DIRNAME = os.path.join(".ruka", "checkpoints")


def checkpoint_root(base_dir: str) -> str:
    return os.path.join(base_dir, CHECKPOINT_DIRNAME)


def _within(base: str, target: str) -> bool:
    try:
        base_abs = os.path.abspath(base)
        return os.path.commonpath([base_abs, os.path.abspath(target)]) == base_abs
    except (ValueError, OSError):
        return False


def _rel(base: str, path: str) -> str | None:
    """Path relatif aman terhadap base, atau None bila di luar."""
    try:
        rel = os.path.relpath(os.path.abspath(path), os.path.abspath(base))
    except (ValueError, OSError):
        return None
    if rel in (os.curdir, os.pardir) or rel.startswith(os.pardir + os.sep):
        return None
    if os.path.isabs(rel):
        return None
    return rel


def _abs_target(base: str, rel: str) -> str:
    target = os.path.abspath(os.path.join(base, rel))
    if not _within(base, target):
        raise ValueError(f"path manifest di luar workspace: {rel}")
    return target


def _snapshot_into(manifest, seen, base, group, path, recurse):
    abs_path = os.path.abspath(path)
    rel = _rel(base, abs_path)
    if rel is None or rel in seen:
        return
    if rel == ".ruka" or rel.startswith(".ruka" + os.sep):
        return  # jangan salin checkpoint ke dalam dirinya sendiri
    seen.add(rel)

    if len(manifest["entries"]) >= MAX_ENTRIES:
        manifest["truncated"] = True
        return

    if not os.path.lexists(abs_path):
        manifest["entries"].append({"path": rel, "existed": False, "kind": "file"})
        return

    if os.path.islink(abs_path):
        manifest.setdefault("skipped", []).append(rel)
        return

    if os.path.isdir(abs_path):
        manifest["entries"].append({"path": rel, "existed": True, "kind": "dir"})
        if recurse:
            try:
                children = sorted(os.listdir(abs_path))
            except OSError:
                return
            for child in children:
                _snapshot_into(
                    manifest, seen, base, group, os.path.join(abs_path, child), True
                )
        return

    try:
        size = os.path.getsize(abs_path)
    except OSError:
        manifest.setdefault("skipped", []).append(rel)
        return
    if size > MAX_FILE_BYTES:
        manifest.setdefault("skipped", []).append(rel)
        return

    backup_name = uuid.uuid4().hex.replace("-", "")[:16]
    try:
        shutil.copy2(abs_path, os.path.join(group, backup_name))
    except OSError:
        manifest.setdefault("skipped", []).append(rel)
        return
    manifest["entries"].append(
        {"path": rel, "existed": True, "kind": "file", "backup": backup_name}
    )


def save_before_change(
    base_dir: str,
    paths,
    label: str = "",
    recurse=(),
    keep: int = KEEP_GROUPS,
) -> str | None:
    """Buat checkpoint untuk ``paths``. Returns nama grup, atau None.

    ``recurse`` berisi path yang isinya ikut disalin (untuk delete_folder).
    Kegagalan snapshot tidak boleh menggagalkan tool — mengembalikan None.
    """
    try:
        base = os.path.abspath(base_dir)
        raw_paths = [p for p in paths if p]
        if not raw_paths:
            return None
        recurse_set = {
            os.path.abspath(
                p if os.path.isabs(p) else os.path.join(base, p)
            )
            for p in recurse if p
        }

        root = checkpoint_root(base)
        os.makedirs(root, exist_ok=True)
        # Urutan nama HARUS mengikuti waktu (time_ns), bukan acak: undo memilih
        # grup terakhir secara leksikografis.
        name = (
            time.strftime("%Y%m%d-%H%M%S")
            + f"-{time.time_ns() % 1_000_000_000:09d}"
            + f"-{uuid.uuid4().hex[:6]}"
        )
        group = os.path.join(root, name)
        os.makedirs(group, exist_ok=True)

        manifest = {
            "created_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
            "label": label,
            "entries": [],
        }
        seen = set()
        for path in raw_paths:
            abs_path = os.path.abspath(
                path if os.path.isabs(path) else os.path.join(base, path)
            )
            if not _within(base, abs_path):
                continue
            _snapshot_into(
                manifest,
                seen,
                base,
                group,
                abs_path,
                recurse=abs_path in recurse_set,
            )

        if not manifest["entries"] and not manifest.get("skipped"):
            shutil.rmtree(group, ignore_errors=True)
            return None

        with open(os.path.join(group, "manifest.json"), "w", encoding="utf-8") as f:
            json.dump(manifest, f, ensure_ascii=False, indent=2)

        _prune(root, keep)
        return name
    except Exception:
        return None


def _groups(root: str) -> list[str]:
    try:
        names = [
            n for n in os.listdir(root)
            if os.path.isdir(os.path.join(root, n))
            and os.path.isfile(os.path.join(root, n, "manifest.json"))
        ]
    except OSError:
        return []
    return sorted(names)


def _prune(root: str, keep: int) -> None:
    if keep <= 0:
        return
    groups = _groups(root)
    for name in groups[:-keep]:
        shutil.rmtree(os.path.join(root, name), ignore_errors=True)


def undo_last(base_dir: str) -> str:
    """Pulihkan grup checkpoint terakhir. Returns pesan untuk user."""
    base = os.path.abspath(base_dir)
    root = checkpoint_root(base)
    groups = _groups(root)
    if not groups:
        return "Tidak ada checkpoint untuk dibatalkan."

    name = groups[-1]
    group = os.path.join(root, name)
    try:
        with open(os.path.join(group, "manifest.json"), encoding="utf-8") as f:
            manifest = json.load(f)
        entries = manifest.get("entries", [])
    except (OSError, json.JSONDecodeError) as e:
        return f"Checkpoint '{name}' rusak: {e}"

    failures: list[str] = []
    restored = removed = 0

    # 1) Pulihkan file yang dulu ada, 2) pastikan folder ada.
    for entry in entries:
        if not entry.get("existed"):
            continue
        try:
            target = _abs_target(base, entry["path"])
            if entry.get("kind") == "dir":
                os.makedirs(target, exist_ok=True)
                continue
            backup = os.path.join(group, entry.get("backup", ""))
            if not os.path.isfile(backup):
                failures.append(entry["path"])
                continue
            os.makedirs(os.path.dirname(target) or base, exist_ok=True)
            if os.path.islink(target) or os.path.isdir(target):
                # Jangan menulis menembus symlink / menimpa folder.
                if os.path.isdir(target) and not os.path.islink(target):
                    shutil.rmtree(target)
                else:
                    os.unlink(target)
            shutil.copy2(backup, target)
            restored += 1
        except (OSError, ValueError, KeyError):
            failures.append(entry.get("path", "?"))

    # 3) Hapus yang dulu belum ada (file/folder hasil tool), terdalam dulu.
    missing = [e for e in entries if not e.get("existed")]
    missing.sort(key=lambda e: e.get("path", "").count(os.sep), reverse=True)
    for entry in missing:
        try:
            target = _abs_target(base, entry["path"])
            if not os.path.lexists(target):
                continue
            if os.path.isdir(target) and not os.path.islink(target):
                shutil.rmtree(target)
            else:
                os.unlink(target)
            removed += 1
        except (OSError, ValueError, KeyError):
            failures.append(entry.get("path", "?"))

    label = manifest.get("label") or "perubahan terakhir"
    skipped = manifest.get("skipped") or []
    truncated = manifest.get("truncated")

    if failures:
        return (
            f"Undo '{label}' sebagian gagal ({len(failures)} item): "
            + ", ".join(failures[:5])
            + ". Checkpoint TIDAK dihapus agar bisa dicoba lagi."
        )

    shutil.rmtree(group, ignore_errors=True)
    msg = f"Undo '{label}': {restored} file dipulihkan"
    if removed:
        msg += f", {removed} file/folder baru dihapus"
    msg += "."
    if skipped:
        msg += f" {len(skipped)} file dilewati (terlalu besar/symlink)."
    if truncated:
        msg += " Sebagian isi folder tidak tersimpan (melebihi 500 item)."
    return msg
