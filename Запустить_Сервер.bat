@echo off
chcp 65001 > nul
title Локальный Агент DeepSeek Pro
cd /d "%~dp0"

echo ========================================================
echo    🚀 Запуск сервера DeepSeek Agent Pro...
echo    🟢 Адрес сервера: http://127.0.0.1:4050
echo ========================================================
echo.

python -c "import send2trash, requests" 2>nul
if errorlevel 1 (
    echo 📦 Установка необходимых библиотек (send2trash, requests)...
    pip install -r requirements.txt
    echo.
)

python -u agent_server.py

pause
