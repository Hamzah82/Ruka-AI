"""Diagnosa: kenapa _summarize_detailed gagal (compacted=False)?"""
import sys, os, importlib.util, traceback
sys.path.insert(0, '.')
os.environ.setdefault('DISPLAY', ':0')
spec = importlib.util.spec_from_file_location('ruka', 'main.py')
M = importlib.util.module_from_spec(spec)
src = open('main.py').read()
i = src.find('if __name__')
exec(compile(src[:i], 'main.py', 'exec'), M.__dict__)

print("=== Diagnosa compacting ===\n")
print(f"ENABLE_COMPACTION : {M.config.ENABLE_COMPACTION}")
print(f"COMPACT_KEEP_TURNS: {M.config.COMPACT_KEEP_TURNS}")
print(f"COMPACT_MODEL     : {M.config.COMPACT_MODEL}")
print(f"MODEL aktif       : {M.MODEL}")
print(f"API_URL           : {M.API_URL}")
print()

# Test _summarize_chunk_detailed dengan pesan sederhana (API asli)
print("=== Test _summarize_chunk_detailed (API asli) ===")
test_msgs = [
    {"role": "user", "content": "apa itu python?"},
    {"role": "assistant", "content": "python adalah bahasa pemrograman"},
]
try:
    result = M._summarize_chunk_detailed(test_msgs)
    print(f"  Hasil: {repr(result[:200])}")
    if result:
        print("  -> BERHASIL")
    else:
        print("  -> GAGAL (return kosong)")
except Exception as e:
    print(f"  EXCEPTION: {e}")
    traceback.print_exc()

# Test langsung chat() dengan COMPACT_MODEL
print("\n=== Test chat() dengan model compact ===")
try:
    resp = M.chat(
        [{"role": "user", "content": "balas dengan kata: TEST"}],
        include_tools=False,
        quiet=True,
        model=M.config.COMPACT_MODEL,
    )
    print(f"  Model dipakai: {M.config.COMPACT_MODEL}")
    print(f"  Respons: {repr((resp['choices'][0]['message']['content'] or '')[:100])}")
except Exception as e:
    print(f"  EXCEPTION: {type(e).__name__}: {e}")
    traceback.print_exc()
