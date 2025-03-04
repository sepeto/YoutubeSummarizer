@echo off
set GIT="C:\Program Files\Git\cmd\git.exe"

echo Configurando Git...
%GIT% config --global user.name "joseba"
%GIT% config --global user.email "joseba.kayzen@gmail.com"

echo.
echo Inicializando repositorio...
%GIT% init

echo.
echo Agregando archivos...
%GIT% add .

echo.
echo Creando commit...
%GIT% commit -m "Initial commit: YouTube downloader with transcription and summary"

echo.
echo Configurando repositorio remoto...
%GIT% remote add origin https://github.com/sepeto/YoutubeSummarizer.git

echo.
echo Subiendo código...
%GIT% push -u origin main

pause 