#!/usr/bin/env python3
"""
Test suite MENYELURUH untuk fitur MEMORY LINTAS-SESI (cross-session notes) Ruka AI.

Mencakup: CRUD, slugify, format index, mode append/replace, tags, validasi,
auto-inject & refresh, dirty flag, backup, unicode, konkurensi (thread & proses),
crash-safety, dan edge cases.

Jalankan (standalone, tanpa pytest):
    python3 tests/test_memory.py

Atau via pytest (jika terpasang):
    pytest tests/test_memory.py -v
"""
import json
import os
import random
import shutil
import string
import subprocess
import sys
import tempfile
import textwrap
import threading
import time

# ── Setup path & import modul main ────────────────────────────────
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
os.environ.setdefault("DISPLAY", ":0")

import importlib.util
_spec = importlib.util.spec_from_file_location("ruka", os.path.join(ROOT, "main.py"))
M = importlib.util.module_from_spec(_spec)
with open(os.path.join(ROOT, "main.py")) as f:
    _src = f.read()
_idx = _src.find("if __name__")
exec(compile(_src[:_idx], "main.py", "exec"), M.__dict__)

# ── Framework mini (tanpa pytest) ─────────────────────────────────
_PASS = 0
_FAIL = 0
_FAILED = []
_TMP = tempfile.mkdtemp(prefix="ruka_memtest_")
_orig_memdir = M.config.MEMORY_DIR


def reset():
    d = os.path.join(_TMP, "memory")
    if os.path.exists(d):
        shutil.rmtree(d, ignore_errors=True)
    os.makedirs(d, exist_ok=True)
    M.config.MEMORY_DIR = d
    M._memory_dirty = False
    M._memory_index_mtime[0] = None
    return d


def check(name, cond, detail=""):
    global _PASS, _FAIL
    if cond:
        _PASS += 1
    else:
        _FAIL += 1
        _FAILED.append(f"{name} — {detail}")
        print(f"  ❌ {name}  {detail}")


def section(title):
    print(f"\n{'='*66}\n{title}\n{'='*66}")


def run():
    # ── 1. CRUD ──
    section("1. CRUD DASAR")
    reset()
    check("write", "berhasil dibuat" in M.tool_memory_write("n1", "Ket 1", "# Isi 1"))
    check("read", "# Isi 1" in M.tool_memory_read("n1"))
    check("list", "n1" in M.tool_memory_list())
    check("search", "n1" in M.tool_memory_search("Isi"))
    check("delete", "berhasil dihapus" in M.tool_memory_delete("n1"))
    check("delete bersih dari index", "n1" not in M._load_memory_index())

    # ── 2. Slugify ──
    section("2. SLUGIFY")
    for inp, exp in [("Preferensi User", "preferensi-user"), ("A_B", "a-b"),
                     ("  x  ", "x"), ("UPPER", "upper"), ("a.b", "ab"),
                     ("a@#!", "a"), ("", "untitled"), ("...", "untitled")]:
        check(f"slugify({inp!r})={exp}", M._slugify(inp) == exp, M._slugify(inp))
    check("slug panjang dibatasi", len(M._slugify("a"*500)) <= 100)
    check("slug panjang no-collision", M._slugify("a"*300+"X") != M._slugify("a"*300+"Y"))
    check("slug traversal aman", "/" not in M._slugify("../../etc/passwd"))

    # ── 3. Mode ──
    section("3. MODE APPEND / REPLACE")
    reset()
    M.tool_memory_write("n", "ket", "L1")
    M.tool_memory_write("n", "ket", "L2", mode="append")
    c = M.tool_memory_read("n")
    check("append menambah", "L1" in c and "L2" in c and c.index("L1") < c.index("L2"))
    M.tool_memory_write("n", "ket", "ONLY", mode="replace")
    c = M.tool_memory_read("n")
    check("replace menimpa", "ONLY" in c and "L1" not in c)
    check("append ke baru = buat", "berhasil dibuat" in M.tool_memory_write("n2", "k", "x", mode="append"))
    M.tool_memory_write("n3", "k", "awal")
    M.tool_memory_write("n3", "k", "akhir", mode="xyz")
    check("mode invalid = replace", "akhir" in M.tool_memory_read("n3"))

    # ── 4. Tags ──
    section("4. TAGS")
    reset()
    M.tool_memory_write("t", "k", "i", tags=["a", "b"])
    check("tags list", M._load_memory_index()["t"]["tags"] == ["a", "b"])
    M.tool_memory_write("t", "k2", "i2")
    check("tags dipertahankan", M._load_memory_index()["t"]["tags"] == ["a", "b"])
    M.tool_memory_write("t2", "k", "i", tags="x, y , z")
    check("tags CSV", M._load_memory_index()["t2"]["tags"] == ["x", "y", "z"])
    M.tool_memory_write("t3", "k", "i", tags=[1, "ok", None, ""])
    check("tags non-string", all(isinstance(x, str) for x in M._load_memory_index()["t3"]["tags"]))

    # ── 5. Validasi ──
    section("5. VALIDASI INPUT")
    reset()
    check("desc kosong ditolak", "wajib" in M.tool_memory_write("x", "", "i").lower())
    check("nama kosong→untitled", "untitled" in M.tool_memory_write("", "k", "i"))
    check("search kosong ditolak", "Error" in M.tool_memory_search(""))
    check("read tak ada", "Error" in M.tool_memory_read("zzz"))
    check("delete tak ada", "Error" in M.tool_memory_delete("zzz"))

    # ── 6. Format index ──
    section("6. FORMAT INDEX")
    d = reset()
    with open(os.path.join(d, "index.json"), "w") as f:
        json.dump({"notes": {"a": {"description": "d"}}, "updated_at": "x"}, f)
    check("format {notes:{}}", "a" in M._load_memory_index())
    with open(os.path.join(d, "index.json"), "w") as f:
        json.dump({"b": {"description": "d"}}, f)
    check("format flat", "b" in M._load_memory_index())
    with open(os.path.join(d, "index.json"), "w") as f:
        f.write("{rusak!!!")
    check("index rusak → {}", M._load_memory_index() == {})
    open(os.path.join(d, "index.json"), "w").close()
    check("index 0-byte → {}", M._load_memory_index() == {})

    # ── 7. Auto-inject ──
    section("7. AUTO-INJECT & REFRESH")
    reset()
    check("section kosong", "Belum ada catatan" in M._build_memory_section())
    M.tool_memory_write("a", "Ket A", "i")
    sec = M._build_memory_section()
    check("section berisi", "a" in sec and "Ket A" in sec)
    check("marker ada", M._MEMORY_START in sec and M._MEMORY_END in sec)
    sp = M.get_system_prompt("t")
    check("system prompt punya marker", M._MEMORY_START in sp)
    check("system prompt punya catatan", "Ket A" in sp)
    msgs = [{"role": "system", "content": sp}]
    M.tool_memory_write("b", "Ket B", "i")
    check("refresh true", M._refresh_memory_in_prompt(msgs) is True)
    check("refresh tampil baru", "Ket B" in msgs[0]["content"])
    for _ in range(10):
        M._refresh_memory_in_prompt(msgs)
    # Hitung BLOK lengkap (pasangan marker), bukan sekadar kemunculan string
    # marker — teks lain boleh menyebut nama marker tanpa dianggap blok.
    import re as _re
    _blocks = _re.findall(
        _re.escape(M._MEMORY_START) + r".*?" + _re.escape(M._MEMORY_END),
        msgs[0]["content"], _re.DOTALL,
    )
    check("refresh 10x tetap 1 blok", len(_blocks) == 1, f"blok={len(_blocks)}")
    check("prompt lain utuh", "Kamu adalah Ruka AI" in msgs[0]["content"])
    check("prompt lain utuh (skill)", "SKILL TAMBAHAN" in msgs[0]["content"])
    check("tanpa marker = noop", M._refresh_memory_in_prompt([{"role":"system","content":"x"}]) is False)

    # ── 8. Fingerprint / cross-session ──
    section("8. DETEKSI PERUBAHAN DARI SESI LAIN")
    reset()
    msgs = [{"role": "system", "content": M.get_system_prompt("t")}]
    M._memory_index_mtime[0] = M._memory_index_fingerprint()
    M._memory_dirty = False
    check("tanpa perubahan = False", M._memory_maybe_refresh(msgs) is False)
    M.tool_memory_write("luar", "Dari sesi lain", "i")
    M._memory_dirty = False
    check("perubahan terdeteksi", M._memory_maybe_refresh(msgs) is True)
    check("catatan luar muncul", "luar" in msgs[0]["content"])

    # ── 9. Dirty flag ──
    section("9. DIRTY FLAG")
    reset()
    M._memory_dirty = False
    M.tool_memory_write("a", "k", "i")
    check("write → dirty", M._memory_dirty is True)
    M._memory_dirty = False
    M.tool_memory_delete("a")
    check("delete → dirty", M._memory_dirty is True)

    # ── 10. Backup & crash-safety ──
    section("10. BACKUP & CRASH-SAFETY")
    reset()
    M.tool_memory_write("a", "k", "i")
    M.tool_memory_write("b", "k", "i")
    bak = os.path.join(M.config.MEMORY_DIR, "backups", "index.json.bak")
    check("backup terbentuk", os.path.exists(bak))
    try:
        json.load(open(bak)); check("backup valid JSON", True)
    except Exception as e:
        check("backup valid JSON", False, str(e))
    for i in range(10):
        M.tool_memory_write(f"c{i}", f"k{i}", "i")
    check("tak ada .tmp tertinggal",
          not [f for f in os.listdir(M.config.MEMORY_DIR) if f.startswith(".tmp")])
    try:
        json.load(open(os.path.join(M.config.MEMORY_DIR, "index.json")))
        check("index selalu valid JSON", True)
    except Exception as e:
        check("index selalu valid JSON", False, str(e))

    # ── 11. Unicode & konten khusus ──
    section("11. UNICODE & KONTEN KHUSUS")
    reset()
    M.tool_memory_write("emoji", "Ket 🐢", "# 🐢 日本語 العربية")
    c = M.tool_memory_read("emoji")
    check("unicode", "🐢" in c and "日本語" in c and "العربية" in c)
    M.tool_memory_write("js", 'kutip " \\ {}', '{"k":"v"}')
    check("karakter JSON khusus", '{"k":"v"}' in M.tool_memory_read("js"))
    M.tool_memory_write("kosong", "k", "")
    check("konten kosong", "kosong" in M.tool_memory_read("kosong"))
    M.tool_memory_write("nl", "k\nb2", "Isi\n\nparagraf")
    check("newline", "paragraf" in M.tool_memory_read("nl"))
    big = "x" * (512 * 1024)
    check("konten 512KB", "berhasil" in M.tool_memory_write("big", "k", big))
    check("512KB terbaca utuh", len(M.tool_memory_read("big")) >= len(big))

    # ── 12. Orphan & sinkronisasi ──
    section("12. ORPHAN & SINKRONISASI")
    reset()
    M.tool_memory_write("orphan", "k", "i")
    os.remove(os.path.join(M.config.MEMORY_DIR, "orphan.md"))
    check("index tanpa file → error", "Error" in M.tool_memory_read("orphan") or "sinkron" in M.tool_memory_read("orphan"))
    with open(os.path.join(M.config.MEMORY_DIR, "manual.md"), "w") as f:
        f.write("# manual")
    check("file tanpa index tak crash", isinstance(M.tool_memory_list(), str))
    reset()
    M.tool_memory_write("NamaCatatan", "v1", "v1")
    M.tool_memory_write("namacatatan", "v2", "v2")
    check("case-insensitive = 1 catatan", len(M._load_memory_index()) == 1)
    M.tool_memory_write("reuse", "v1", "lama")
    M.tool_memory_delete("reuse")
    M.tool_memory_write("reuse", "v2", "baru")
    check("reuse setelah delete", "baru" in M.tool_memory_read("reuse"))
    M.tool_memory_write("a", "k", "i")
    shutil.rmtree(M.config.MEMORY_DIR, ignore_errors=True)
    check("auto-recreate folder", "berhasil" in M.tool_memory_write("b", "k", "i"))

    # ── 13. Banyak catatan ──
    section("13. BANYAK CATATAN")
    reset()
    for i in range(100):
        M.tool_memory_write(f"c{i:03d}", f"Ket {i}", f"isi {i}")
    idx = M._load_memory_index()
    check("100 catatan", len(idx) == 100, str(len(idx)))
    sec = M._build_memory_section()
    check("semua di section", all(f"c{i:03d}" in sec for i in range(100)))
    check("100 file .md", len([f for f in os.listdir(M.config.MEMORY_DIR) if f.endswith(".md")]) == 100)

    # ── 14. Konkurensi thread ──
    section("14. KONKURENSI (THREAD)")
    reset()
    def w(pre, n):
        for i in range(n):
            M.tool_memory_write(f"{pre}-{i:02d}", f"k {i}", "i")
    t1 = threading.Thread(target=w, args=("ta", 20)); t2 = threading.Thread(target=w, args=("tb", 20))
    t1.start(); t2.start(); t1.join(); t2.join()
    idx = M._load_memory_index()
    check("thread: 20+20", sum(1 for k in idx if k.startswith("ta-")) == 20 and
          sum(1 for k in idx if k.startswith("tb-")) == 20)
    reset()
    def w2(pre, n):
        for i in range(n):
            M.tool_memory_write("shared", "k", f"b-{pre}-{i:02d}", mode="append")
    t1 = threading.Thread(target=w2, args=("X", 20)); t2 = threading.Thread(target=w2, args=("Y", 20))
    t1.start(); t2.start(); t1.join(); t2.join()
    c = open(os.path.join(M.config.MEMORY_DIR, "shared.md")).read()
    check("thread append same-note 20+20", c.count("b-X-") == 20 and c.count("b-Y-") == 20)

    # ── 15. Konkurensi proses ──
    section("15. KONKURENSI (PROSES)")
    reset()
    worker = textwrap.dedent(f'''
        import sys, os, importlib.util
        sys.path.insert(0, {ROOT!r})
        os.environ["DISPLAY"] = ":0"
        spec = importlib.util.spec_from_file_location("ruka", {os.path.join(ROOT,"main.py")!r})
        mod = importlib.util.module_from_spec(spec)
        with open({os.path.join(ROOT,"main.py")!r}) as f:
            src = f.read()
        idx = src.find("if __name__")
        exec(compile(src[:idx], "main.py", "exec"), mod.__dict__)
        mod.config.MEMORY_DIR = {M.config.MEMORY_DIR!r}
        pre = sys.argv[1]; n = int(sys.argv[2])
        for i in range(n):
            mod.tool_memory_write(f"{{pre}}-{{i:02d}}", f"k {{i}}", "i")
    ''')
    wf = os.path.join(_TMP, "worker.py")
    with open(wf, "w") as f:
        f.write(worker)
    ps = [subprocess.Popen([sys.executable, wf, "pa", "25"]),
          subprocess.Popen([sys.executable, wf, "pb", "25"])]
    for p in ps:
        p.wait()
    idx = M._load_memory_index()
    check("proses: 25+25", sum(1 for k in idx if k.startswith("pa-")) == 25 and
          sum(1 for k in idx if k.startswith("pb-")) == 25)

    # ── 16. Chaos (operasi acak) ──
    section("16. CHAOS (500 OPERASI ACAK)")
    reset()
    random.seed(99)
    names = ["a", "b", "Preferensi User", "x"*300, "!!!", "", "日本", "n.d"]
    errs = 0
    for i in range(500):
        op = random.choice(["write", "write", "write", "read", "delete", "search", "list"])
        try:
            if op == "write":
                M.tool_memory_write(random.choice(names),
                                    random.choice(["k", "", "k"*100]),
                                    random.choice(["", "i", "x"*1000, "🐢", '{"j":1}']),
                                    tags=random.choice([None, ["a"], "x,y", []]),
                                    mode=random.choice(["replace", "append", "zzz"]))
            elif op == "read":
                M.tool_memory_read(random.choice(names))
            elif op == "delete":
                M.tool_memory_delete(random.choice(names))
            elif op == "search":
                M.tool_memory_search(random.choice(["a", "🐢", "zzz"]))
            else:
                M.tool_memory_list()
        except Exception as e:
            errs += 1
    check("500 op tanpa error", errs == 0, f"{errs} error")
    idx = M._load_memory_index()
    missing = [s for s in idx if not os.path.exists(os.path.join(M.config.MEMORY_DIR, f"{s}.md"))]
    check("index↔file konsisten", not missing, str(missing[:3]))
    try:
        json.load(open(os.path.join(M.config.MEMORY_DIR, "index.json")))
        check("index valid setelah chaos", True)
    except Exception as e:
        check("index valid setelah chaos", False, str(e))

    # ── 17. Integrasi: memory selamat dari compaction ──
    section("17. INTEGRASI DENGAN COMPACTION")
    reset()
    M.tool_memory_write("penting", "Catatan penting", "# Jangan hilang")
    M.chat = lambda messages, **kw: {"choices": [{"message": {"content": "RINGKASAN"}}]}
    msgs = [{"role": "system", "content": M.get_system_prompt("t")}]
    for i in range(40):
        msgs.append({"role": "user", "content": f"u{i} " + "x"*100})
        msgs.append({"role": "assistant", "content": f"a{i} " + "y"*100})
    _orig_mh = M.config.MAX_HISTORY_TOKENS
    M.config.MAX_HISTORY_TOKENS = 100
    new_msgs, compacted, _ = M.compact_history(msgs, force=True)
    M.config.MAX_HISTORY_TOKENS = _orig_mh
    check("compaction jalan", compacted)
    check("memory selamat", "penting" in new_msgs[0]["content"])
    check("marker selamat", M._MEMORY_START in new_msgs[0]["content"])
    check("prompt utama selamat", "Kamu adalah Ruka AI" in new_msgs[0]["content"])

    # ── 18. .gitignore ──
    section("18. GITIGNORE")
    gi = open(os.path.join(ROOT, ".gitignore")).read()
    check("data/ di gitignore", "data/" in gi)

    # ── Regresi blok memory ──
    run_regression()


# ── Runner ────────────────────────────────────────────────────────
def main():
    print("╔" + "═"*64 + "╗")
    print("║  TEST SUITE MEMORY LINTAS-SESI — Ruka AI".ljust(65) + "║")
    print("╚" + "═"*64 + "╝")
    try:
        run()
    finally:
        shutil.rmtree(_TMP, ignore_errors=True)
        M.config.MEMORY_DIR = _orig_memdir

    print("\n" + "="*66)
    print(f"HASIL: {_PASS} lulus, {_FAIL} gagal")
    print("="*66)
    if _FAILED:
        print("\nYANG GAGAL:")
        for f in _FAILED:
            print("  -", f)
        return 1
    print("\n🎉 SEMUA TEST LULUS!")
    return 0


def run_regression():
    """Test regresi: bug marker palsu di system prompt."""
    section("REGRESI: BLOK MEMORY DI SYSTEM PROMPT")
    reset()
    import re as _re
    M.tool_memory_write("x", "Ket X", "isi")
    sp = M.get_system_prompt("t")
    blocks = _re.findall(
        _re.escape(M._MEMORY_START) + r".*?" + _re.escape(M._MEMORY_END),
        sp, _re.DOTALL,
    )
    check("1 blok memory di system prompt", len(blocks) == 1, f"blok={len(blocks)}")
    check("blok memory berisi catatan", "Ket X" in (blocks[0] if blocks else ""))

    reset()
    M.tool_memory_write("a", "Ket A", "isi")
    msgs = [{"role": "system", "content": M.get_system_prompt("t")}]
    before = msgs[0]["content"]
    check("catatan awal ada", "Ket A" in before)
    M.tool_memory_write("b", "Keterangan " + "panjang " * 50, "isi")
    check("refresh jalan", M._refresh_memory_in_prompt(msgs) is True)
    after = msgs[0]["content"]
    check("blok memory bertambah (refresh tepat sasaran)",
          len(after) > len(before), f"{len(before)} -> {len(after)}")
    check("catatan baru & lama ada", "b" in after and "Ket A" in after)


# ── Entry point untuk pytest ──────────────────────────────────────
def test_memory_suite():
    """Wrapper agar suite ini juga bisa dijalankan via pytest."""
    global _PASS, _FAIL, _FAILED
    _PASS = 0
    _FAIL = 0
    _FAILED = []
    try:
        run()
    finally:
        shutil.rmtree(_TMP, ignore_errors=True)
        M.config.MEMORY_DIR = _orig_memdir
    assert _FAIL == 0, "Gagal: " + "; ".join(_FAILED)


if __name__ == "__main__":
    sys.exit(main())
