@echo off
chcp 65001 > nul
title Настройки Резервных Копий (Бэкапов) DeepSeek
cd /d "%~dp0"

python manage_backups.py

pause
