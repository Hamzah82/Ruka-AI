# Konfigurasi dinamis dari config.json dan config.py

import os
import json

CONFIG_JSON_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.json")

def load_config_from_json():
    """Load konfigurasi dari config.json jika ada."""
    if not os.path.exists(CONFIG_JSON_PATH):
        return None
    try:
        with open(CONFIG_JSON_PATH, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError) as e:
        print(f"Warning: Gagal baca config.json: {e}")
        return None

def get_dynamic_config():
    """Gabungkan config.json + config.py dengan prioritas ke config.json."""
    json_config = load_config_from_json()
    import config
    
    result = {}
    
    # API settings - priority to config.json
    if json_config and 'api_endpoint' in json_config:
        result['API_URL'] = json_config['api_endpoint']
    else:
        result['API_URL'] = config.API_URL
    
    if json_config and 'model' in json_config:
        model_val = json_config['model'].strip()
        result['MODEL'] = model_val if model_val else config.MODEL
    else:
        result['MODEL'] = config.MODEL
    
    # Vision model (analisis gambar) — priority config.json, fallback config.py
    if json_config and 'vision_model' in json_config:
        vision_val = json_config['vision_model'].strip()
        result['VISION_MODEL'] = vision_val if vision_val else config.VISION_MODEL
    else:
        result['VISION_MODEL'] = config.VISION_MODEL
    
    # Compact model (ringkas riwayat) — priority config.json, fallback config.py
    if json_config and 'compact_model' in json_config:
        compact_val = (json_config['compact_model'] or "").strip()
        result['COMPACT_MODEL'] = compact_val if compact_val else config.COMPACT_MODEL
    else:
        result['COMPACT_MODEL'] = config.COMPACT_MODEL
    
    api_key_json = ""
    if json_config and 'api_key' in json_config:
        api_key_json = json_config['api_key'].strip()
    
    api_key_env = os.getenv("OPENROUTER_API_KEY", "")
    result['OPENROUTER_API_KEY'] = api_key_env if api_key_env else api_key_json
    
    result['HEADERS'] = {
        "Authorization": f"Bearer {result['OPENROUTER_API_KEY']}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://myapp.com",
        "X-Title": "Ruka AI - Kura-Kura Agent",
    }
    
    # All other settings from config.py
    result['BASE_DIR'] = config.BASE_DIR
    result['SCRIPT_DIR'] = config.SCRIPT_DIR
    result['SESSIONS_DIR'] = config.SESSIONS_DIR
    result['MEMORY_DIR'] = getattr(config, 'MEMORY_DIR', os.path.join(config.SCRIPT_DIR, "data", "memory"))
    result['DEFAULT_CMD_TIMEOUT'] = config.DEFAULT_CMD_TIMEOUT
    result['MAX_RETRIES'] = config.MAX_RETRIES
    result['RETRY_BASE_DELAY'] = config.RETRY_BASE_DELAY
    result['MAX_READ_LINES'] = config.MAX_READ_LINES
    result['MAX_READ_CHARS'] = config.MAX_READ_CHARS
    result['MAX_EXEC_OUTPUT_CHARS'] = config.MAX_EXEC_OUTPUT_CHARS
    result['BINARY_SNIFF_BYTES'] = config.BINARY_SNIFF_BYTES
    result['TRUNCATION_THRESHOLD'] = config.TRUNCATION_THRESHOLD
    result['MAX_HISTORY_TOKENS'] = config.MAX_HISTORY_TOKENS
    result['COMPACT_KEEP_TURNS'] = getattr(config, 'COMPACT_KEEP_TURNS', 5)
    result['ENABLE_COMPACTION'] = getattr(config, 'ENABLE_COMPACTION', True)
    result['COMPACT_CHUNK_TOKENS'] = getattr(config, 'COMPACT_CHUNK_TOKENS', 700000)
    result['COMPACT_MAX_CHARS'] = getattr(config, 'COMPACT_MAX_CHARS', 120000)
    result['COMPACT_TEMPERATURE'] = getattr(config, 'COMPACT_TEMPERATURE', 0.3)
    result['COMPACT_MAX_TOKENS'] = getattr(config, 'COMPACT_MAX_TOKENS', 16000)
    result['COMPACT_MSG_MAX_CHARS'] = getattr(config, 'COMPACT_MSG_MAX_CHARS', 12000)
    result['ESTIMATE_CHARS_PER_TOKEN'] = getattr(config, 'ESTIMATE_CHARS_PER_TOKEN', 4)
    result['NOTIF_ENABLED'] = getattr(config, 'NOTIF_ENABLED', False)
    result['NOTIF_SOUND'] = getattr(config, 'NOTIF_SOUND', "complete")
    result['NOTIF_SOUND_DIRS'] = getattr(config, 'NOTIF_SOUND_DIRS', [])
    result['BLOCKED_COMMANDS'] = config.BLOCKED_COMMANDS
    
    return result
