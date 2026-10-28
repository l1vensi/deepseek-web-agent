import os
import sys
import json
import time
from pathlib import Path

# Ensure UTF-8 output on Windows
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stdin.reconfigure(encoding="utf-8")
    except Exception:
        pass

BASE_DIR = Path(__file__).resolve().parent
CONFIG_FILE = BASE_DIR / "backup_config.json"
BACKUPS_DIR = BASE_DIR / ".agent_backups"

DEFAULT_CONFIG = {
    "backup_enabled": True,
    "retention_days": 7,
    "max_backup_files": 100
}

def load_config():
    if not CONFIG_FILE.exists():
        save_config(DEFAULT_CONFIG)
        return DEFAULT_CONFIG.copy()
    try:
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            return {
                "backup_enabled": bool(data.get("backup_enabled", True)),
                "retention_days": int(data.get("retention_days", 7)),
                "max_backup_files": int(data.get("max_backup_files", 100))
            }
    except Exception:
        return DEFAULT_CONFIG.copy()

def save_config(cfg):
    try:
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(cfg, f, indent=4, ensure_ascii=False)
        return True
    except Exception as e:
        print(f"❌ Ошибка сохранения настроек: {e}")
        return False

def get_backups_info():
    if not BACKUPS_DIR.exists():
        return 0, 0.0, None, None
    files = [f for f in BACKUPS_DIR.iterdir() if f.is_file() and f.name != "trash_index.json"]
    count = len(files)
    total_bytes = sum(f.stat().st_size for f in files)
    total_mb = total_bytes / (1024 * 1024)
    if count > 0:
        sorted_files = sorted(files, key=lambda x: x.stat().st_mtime)
        oldest = time.strftime("%d.%m.%Y %H:%M", time.localtime(sorted_files[0].stat().st_mtime))
        newest = time.strftime("%d.%m.%Y %H:%M", time.localtime(sorted_files[-1].stat().st_mtime))
    else:
        oldest = None
        newest = None
    return count, total_mb, oldest, newest

def perform_cleanup(retention_days, max_files):
    if not BACKUPS_DIR.exists():
        return 0
    now = time.time()
    deleted = 0
    files = [f for f in BACKUPS_DIR.iterdir() if f.is_file() and f.name != "trash_index.json"]
    
    # 1. По сроку
    if retention_days > 0:
        cutoff = now - (retention_days * 86400)
        for f in files:
            try:
                if f.stat().st_mtime < cutoff:
                    f.unlink(missing_ok=True)
                    deleted += 1
            except Exception:
                pass
                
    # 2. По лимиту
    remaining = sorted([f for f in BACKUPS_DIR.iterdir() if f.is_file() and f.name != "trash_index.json"], key=lambda x: x.stat().st_mtime)
    if len(remaining) > max_files:
        to_del = len(remaining) - max_files
        for old_f in remaining[:to_del]:
            try:
                old_f.unlink(missing_ok=True)
                deleted += 1
            except Exception:
                pass
    return deleted

def wipe_all_backups():
    if not BACKUPS_DIR.exists():
        return 0
    deleted = 0
    for f in BACKUPS_DIR.iterdir():
        if f.is_file() and f.name != "trash_index.json":
            try:
                f.unlink(missing_ok=True)
                deleted += 1
            except Exception:
                pass
    return deleted

def print_menu():
    cfg = load_config()
    count, total_mb, oldest, newest = get_backups_info()
    
    status_str = "🟢 ВКЛЮЧЕНО" if cfg["backup_enabled"] else "🔴 ВЫКЛЮЧЕНО"
    if cfg["retention_days"] == 0:
        retention_str = "Бессрочно (хранить вечно)"
    elif cfg["retention_days"] == 1:
        retention_str = "1 день (24 часа)"
    elif cfg["retention_days"] in (2, 3, 4):
        retention_str = f"{cfg['retention_days']} дня"
    else:
        retention_str = f"{cfg['retention_days']} дней"
        
    print("\n" + "=" * 65)
    print(" 🛡️  ПАНЕЛЬ УПРАВЛЕНИЯ РЕЗЕРВНЫМИ КОПИЯМИ (DEEPSEEK BACKUPS)")
    print("=" * 65)
    print(f" • Создание бэкапов:      {status_str}")
    print(f" • Срок хранения:         {retention_str}")
    print(f" • Лимит файлов:          {cfg['max_backup_files']} шт")
    print(f" • Сейчас на диске:       {count} копий ({total_mb:.2f} МБ)")
    if oldest and newest:
        print(f" • Период копий:          от {oldest} до {newest}")
    print("=" * 65)
    print(" [1] Переключить режим (Включить / Выключить)")
    print(" [2] Изменить срок хранения (в днях: 1, 3, 7, 14, 30 или 0)")
    print(" [3] Изменить лимит файлов (например 50, 100, 300)")
    print(" [4] Очистить устаревшие копии прямо сейчас")
    print(" [5] Удалить ВСЕ бэкапы (полное освобождение диска)")
    print(" [0] Выход")
    print("=" * 65)

def main():
    while True:
        print_menu()
        try:
            choice = input("Выберите пункт меню [0-5]: ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\nВыход из меню.")
            break
            
        cfg = load_config()
        
        if choice == "1":
            cfg["backup_enabled"] = not cfg["backup_enabled"]
            save_config(cfg)
            new_state = "ВКЛЮЧЕНЫ" if cfg["backup_enabled"] else "ВЫКЛЮЧЕНЫ"
            print(f"\n✅ Режим обновлен! Создание бэкапов: {new_state}")
            
        elif choice == "2":
            print("\nУкажите срок хранения бэкапов в днях:")
            print("  (Введите 7 для недели, 14 для двух недель, 1 для суток, или 0 для вечного хранения)")
            val = input("Срок в днях [сейчас: {}]: ".format(cfg["retention_days"])).strip()
            if val.isdigit():
                cfg["retention_days"] = int(val)
                save_config(cfg)
                print(f"✅ Срок хранения установлен: {cfg['retention_days']} дн.")
            else:
                print("⚠️ Введено не число, значение не изменено.")
                
        elif choice == "3":
            print("\nУкажите максимальное количество хранимых файлов:")
            val = input("Лимит файлов [сейчас: {}]: ".format(cfg["max_backup_files"])).strip()
            if val.isdigit() and int(val) > 0:
                cfg["max_backup_files"] = int(val)
                save_config(cfg)
                print(f"✅ Лимит файлов установлен: {cfg['max_backup_files']} шт.")
            else:
                print("⚠️ Некорректное значение, лимит не изменен.")
                
        elif choice == "4":
            deleted = perform_cleanup(cfg["retention_days"], cfg["max_backup_files"])
            print(f"\n🧹 Очистка выполнена! Удалено устаревших копий: {deleted}")
            
        elif choice == "5":
            confirm = input("\n⚠️ Вы уверены, что хотите удалить ВСЕ существующие бэкапы? (да/нет): ").strip().lower()
            if confirm in ("да", "yes", "y", "д"):
                deleted = wipe_all_backups()
                print(f"💥 Все резервные копии удалены! Освобождено файлов: {deleted}")
            else:
                print("Отменено.")
                
        elif choice == "0":
            print("\nЗавершение работы.")
            break
        else:
            print("⚠️ Неизвестный пункт меню. Выберите от 0 до 5.")

if __name__ == "__main__":
    main()
