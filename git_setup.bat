@echo off
echo ============================================
echo Configuracion de Git para YouTube Downloader
echo ============================================
echo.

set GIT="C:\Program Files\Git\cmd\git.exe"

echo [1/7] Verificando Git...
%GIT% --version
if errorlevel 1 (
    echo ERROR: Git no esta instalado o no se encuentra en el PATH
    pause
    exit /b 1
)

echo.
echo [2/7] Inicializando repositorio...
%GIT% init
if errorlevel 1 (
    echo ERROR: No se pudo inicializar el repositorio
    pause
    exit /b 1
)

echo.
echo [3/7] Configurando usuario...
%GIT% config --global user.name "joseba"
%GIT% config --global user.email "joseba.kayzen@gmail.com"

echo.
echo [4/7] Agregando archivos...
%GIT% add .
if errorlevel 1 (
    echo ERROR: No se pudieron agregar los archivos
    pause
    exit /b 1
)

echo.
echo [5/7] Creando commit inicial...
%GIT% commit -m "Initial commit: YouTube downloader with transcription and summary"
if errorlevel 1 (
    echo ERROR: No se pudo crear el commit
    pause
    exit /b 1
)

echo.
echo [6/7] Configurando repositorio remoto...
%GIT% remote remove origin
%GIT% remote add origin https://github.com/sepeto/YoutubeSummarizer.git
if errorlevel 1 (
    echo ERROR: No se pudo configurar el repositorio remoto
    pause
    exit /b 1
)

echo.
echo [7/7] Subiendo código...
echo NOTA: Si te pide credenciales, usa tu token de acceso personal de GitHub
%GIT% push -u origin main
if errorlevel 1 (
    echo ERROR: No se pudo subir el código
    echo.
    echo Solucion:
    echo 1. Ve a https://github.com/settings/tokens
    echo 2. Genera un nuevo token con permisos 'repo'
    echo 3. Usa ese token como contraseña
    pause
    exit /b 1
)

echo.
echo ============================================
echo ¡Proceso completado con éxito!
echo ============================================
echo.
echo Tu código está disponible en:
echo https://github.com/sepeto/YoutubeSummarizer
echo.
pause 