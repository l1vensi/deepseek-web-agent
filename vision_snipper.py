import os
import sys
import time
import subprocess
from pathlib import Path
from PIL import ImageGrab

BASE_DIR = Path(__file__).resolve().parent
VISION_DIR = BASE_DIR / ".agent_vision"
VISION_DIR.mkdir(parents=True, exist_ok=True)
OUTPUT_FILE = VISION_DIR / "latest_snip.png"

def run_native_snip():
    print("=" * 60)
    print(" 👁️  ЗРЕНИЕ DEEPSEEK: ВЫБОР ОБЛАСТИ ЭКРАНА")
    print("=" * 60)
    print(" Сейчас откроется системная рамка Windows (Ножницы).")
    print(" 1. Выделите мышкой нужную область экрана.")
    print(" 2. Снимок автоматически сохранится и скопируется в буфер.")
    print(" 3. Перейдите в чат DeepSeek и нажмите Ctrl+V для отправки!")
    print("=" * 60)
    
    # Запуск нативного инструмента Windows 10/11
    try:
        subprocess.run(["cmd.exe", "/c", "start", "ms-screenclip:"], check=True)
    except Exception as e:
        print(f"⚠️ Ошибка вызова ms-screenclip: {e}")
        return False
        
    print("\n⏳ Ожидание выделения области мышкой (до 30 сек)...")
    start_time = time.time()
    
    # Ждем появления нового изображения в буфере обмена
    captured = False
    for _ in range(60):
        time.sleep(0.5)
        try:
            img = ImageGrab.grabclipboard()
            if img is not None:
                img.save(OUTPUT_FILE, "PNG")
                print(f"\n✅ Снимок успешно сохранен: {OUTPUT_FILE}")
                print(f"📏 Размер изображения: {img.size[0]}x{img.size[1]} пикселей")
                print("📋 Снимок уже находится в буфере обмена Windows!")
                print("👉 Просто откройте вкладку DeepSeek и нажмите Ctrl+V в поле ввода.")
                captured = True
                break
        except Exception:
            pass
            
    if not captured:
        print("\n⌛ Время ожидания истекло или выделение было отменено пользователем.")
    return captured

if __name__ == "__main__":
    run_native_snip()
    print("\nНажмите Enter для закрытия окна...")
    input()
