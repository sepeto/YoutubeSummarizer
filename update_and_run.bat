@echo off
echo [INFO] Iniciando actualización de librerías de descarga...

REM Actualizar solo las librerías de descarga
python -m pip install --upgrade yt-dlp
python -m pip install --upgrade pytube
python -m pip install --upgrade youtube-dl

echo [INFO] Iniciando el programa...
python main.py
pause 