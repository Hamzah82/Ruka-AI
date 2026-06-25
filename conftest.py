import os
import sys

# Pastikan root proyek (tempat main.py & config.py) ada di sys.path agar pytest
# bisa `import main`/`import config` saat dijalankan dari mana pun (lokal & CI).
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
