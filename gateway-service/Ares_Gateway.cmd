@echo off
rem Ares Agent Gateway - Messaging Platform Integration
cd /d C:\Users\krish\AppData\Local\ares
set "ARES_HOME=C:\Users\krish\AppData\Local\ares"
set "PYTHONIOENCODING=utf-8"
set "ARES_GATEWAY_DETACHED=1"
set "VIRTUAL_ENV=C:\Users\krish\AppData\Local\ares\ares-agent\venv"
C:\Users\krish\AppData\Local\ares\ares-agent\venv\Scripts\pythonw.exe -m ares_cli.main gateway run
exit /b 0

