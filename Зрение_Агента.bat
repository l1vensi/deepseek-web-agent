@echo off
chcp 65001 > nul
title Зрение DeepSeek Pro (Снимок экрана)
cd /d "%~dp0"

python vision_snipper.py

