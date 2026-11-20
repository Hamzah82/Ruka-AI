"""Diagnosa: kenapa /compact bilang 'dilewati' padahal riwayat panjang?
Fokus: apakah pre-check di handler BEDA dengan cek di compact_history?"""
import sys, os, importlib.util
sys.path.insert(0, '.')
os.environ.setdefault('DISPLAY', ':0')
spec = importlib.util.spec_from_file_location('ruka', 'main.py')
M = importlib.util.module_from_spec(spec)
src = open('main.py').read()
i = src.find('if __name__')
exec(compile(src[:i], 'main.py', 'exec'), M.__dict__)

print("=== Bandingkan pre-check handler vs cek compact_history ===\n")

# Kasus: riwayat dengan 1 giliran user panjang (banyak pesan assistant/tool)
# Ini yang SERING terjadi di Ruka: 1 prompt user -> banyak round agentic
msgs = [{"role": "system", "content": M.get_system_prompt("t")}]
msgs.append({"role": "user", "content": "kerjakan tugas besar"})
# 20 round agentic dalam SATU giliran
for k in range(20):
    msgs.append({"role": "assistant", "content": None,
                 "tool_calls": [{"id": f"t{k}", "type": "function",
                                 "function": {"name": "read_file", "arguments": "{}"}}]})
    msgs.append({"role": "tool", "tool_call_id": f"t{k}", "content": f"hasil {k}"})
msgs.append({"role": "assistant", "content": "selesai"})

print(f"Total pesan: {len(msgs)}")
print(f"Jumlah giliran user: {sum(1 for m in msgs if m['role']=='user')}")
print()

# Pre-check handler
_head_n = 0
while (_head_n < len(msgs)
       and msgs[_head_n].get("role") == "system"
       and "RINGKASAN PERCAKAPAN SEBELUMNYA" not in (msgs[_head_n].get("content") or "")):
    _head_n += 1
_turns_n = len(M._split_into_turns(msgs[_head_n:]))
_keep = getattr(M.config, "COMPACT_KEEP_TURNS", 5)
print(f"[Pre-check handler]")
print(f"  _head_n = {_head_n}")
print(f"  _turns_n = {_turns_n}")
print(f"  _keep = {_keep}")
print(f"  Hasil: {'LEWATI (belum perlu)' if _turns_n <= _keep else 'LANJUT compact'}")
print()

# Cek compact_history
print(f"[compact_history(force=True)]")
res, compacted, info = M.compact_history(msgs, force=True)
print(f"  compacted = {compacted}")
print(f"  info = {info}")
print()

# KESIMPULAN
print("=== KESIMPULAN ===")
if _turns_n <= _keep and not compacted:
    print("  Penyebab: hanya ada 1 giliran user (banyak pesan tool/assistant")
    print("  dalam SATU giliran). Karena keep_turns=5, tidak ada yang bisa")
    print("  diringkas → compact DILEWATI.")
    print()
    print("  Ini PERILAKU WAJAR, tapi bisa jadi membingungkan user yang")
    print("  melihat riwayat PANJANG (banyak pesan) tapi dianggap 'belum perlu'.")
