#!/usr/bin/env python3
import sys

# Fungsi untuk menambah handle_change_model ke main.py
new_function = '''

# ============================================================
# COMMAND: CHANGE MODEL (ganti model saja)
# ============================================================

def handle_change_model():
    """Command 'ruka model' — interaktif ubah model AI di config.json."""
    
    config_path = os.path.join(SCRIPT_DIR, "config.json")
    
    if not os.path.exists(config_path):
        default_config = {
            "api_endpoint": "https://ai.meongtopup.my.id/v1/chat/completions",
            "model": "meng/deepseek-v4-flash",
            "api_key": "",
            "updated_at": None
        }
        try:
            with open(config_path, "w", encoding="utf-8") as f:
                json.dump(default_config, f, indent=2, ensure_ascii=False)
            print()
            print(f"  {Style.GREY}⏺{Style.RESET} {Style.GREY_LIGHT}File config.json dibuat.{Style.RESET}")
        except Exception as e:
            print(f"\\n  {Style.ERR}⏺{Style.RESET} {Style.ERR}Gagal membuat file config: {e}{Style.RESET}")
            return
    
    try:
        with open(config_path, "r", encoding="utf-8") as f:
            config_data = json.load(f)
        
        current_model = config_data.get("model", "")
        
        print()
        print(f"  {Style.ACCENT}✻{Style.RESET} {Style.BOLD}Ubah Model AI{Style.RESET}")
        print(f"  {_rule()}")
        print(f"  Model saat ini:  {Style.GREY_LIGHT}{current_model or '(kosong)'}{Style.RESET}")
        print()
        
        new_model = input(f"  {Style.ACCENT}❯{Style.RESET} Model baru (Enter untuk tetap '{current_model or '(default)'}'): ").strip()
        if not new_model:
            new_model = current_model
        
        config_data["model"] = new_model if new_model else (config_data.get("model", "") or "meng/deepseek-v4-flash")
        config_data["updated_at"] = datetime.now().isoformat()
        
        with open(config_path, "w", encoding="utf-8") as f:
            json.dump(config_data, f, indent=2, ensure_ascii=False)
        
        with open(config_path, "r", encoding="utf-8") as f:
            saved_data = json.load(f)
        
        msg = (
            f"{Style.OK}✓{Style.RESET} Model berhasil diubah!\\n"
            f"  • Model lama:   {Style.DIM}{current_model}{Style.RESET}\\n"
            f"  • Model baru:   {Style.ACCENT_DIM}{saved_data['model']}{Style.RESET}"
        )
        print(f"\\n{msg}")
        
        print(f"\\n  {Style.GREY}•{Style.RESET} Konfigurasi tersimpan di {Style.GREY_LIGHT}{config_path}{Style.RESET}")
        print(f"  {Style.GREY}•{Style.RESET} Untuk menggunakan model baru, silakan restart Ruka AI.")
        
    except json.JSONDecodeError:
        print(f"\\n  {Style.ERR}⏺{Style.RESET} {Style.ERR}File config.json rusak atau tidak valid JSON.{Style.RESET}")
    except Exception as e:
        print(f"\\n  {Style.ERR}⏺{Style.RESET} {Style.ERR}Terjadi kesalahan: {e}{Style.RESET}")

'''

if __name__ == "__main__":
    print(new_function)
