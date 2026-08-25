# Konfigurasi dinamis dari config.json
# File ini akan di-override oleh values dari config.json

import os
import json

# Path ke config.json
CONFIG_JSON_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.json")

def load_config_from_json():
    """Load konfigurasi dari config.json jika ada."""
    if not os.path.exists(CONFIG_JSON_PATH):
        return None
    
    try:
        with open(CONFIG_JSON_PATH, 'r', encoding='utf-8') as f:
            config_data = json.load(f)
        return config_data
    except (json.JSONDecodeError, IOError) as e:
        print(f"Warning: Gagal baca config.json: {e}")
        return None

def get_dynamic_config():
    """
    Mengembalikan konfigurasi gabungan:
    1. Nilai dari config.json (prioritas tinggi)
    2. Fallback ke config.py jika tidak ada di config.json
    """
    # Load dari config.json
    json_config = load_config_from_json()
    
    # Import default dari config.py
    import config
    
    result = {}
    
    # API Endpoint - prioritas ke config.json
    if json_config and 'api_endpoint' in json_config:
        result['API_URL'] = json_config['api_endpoint']
    else:
        result['API_URL'] = config.API_URL
    
    # Model - prioritas ke config.json
    if json_config and 'model' in json_config:
        model_value = json_config['model'].strip()
        result['MODEL'] = model_value if model_value else config.MODEL
    else:
        result['MODEL'] = config.MODEL
    
    # API Key - prioritaskan config.json atau .env
    api_key_json = ""
    if json_config and 'api_key' in json_config:
        api_key_json = json_config['api_key'].strip()
    
    # Ambil dari env jika ada, atau dari config.json, atau kosong
    api_key_env = os.getenv("OPENROUTER_API_KEY", "")
    result['OPENROUTER_API_KEY'] = api_key_env if api_key_env else api_key_json
    
    # Buat HEADERS dinamis
    result['HEADERS'] = {
        "Authorization": f"Bearer {result['OPENROUTER_API_KEY']}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://myapp.com",
        "X-Title": "Ruka AI - Kura-Kura Agent",
    }
    
    # Configuration lainnya tetap dari config.py
    result['BASE_DIR'] = config.BASE_DIR
    result['SCRIPT_DIR'] = config.SCRIPT_DIR
    result['SESSIONS_DIR'] = config.SESSIONS_DIR
    result['DEFAULT_CMD_TIMEOUT'] = config.DEFAULT_CMD_TIMEOUT
    result['MAX_RETRIES'] = config.MAX_RETRIES
    result['RETRY_BASE_DELAY'] = config.RETRY_BASE_DELAY
    result['BLOCKED_COMMANDS'] = config.BLOCKED_COMMANDS
    
    return result
