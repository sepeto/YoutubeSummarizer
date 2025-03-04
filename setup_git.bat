@echo off
"C:\Program Files\Git\cmd\git.exe" init
"C:\Program Files\Git\cmd\git.exe" config --global user.name "joseba"
"C:\Program Files\Git\cmd\git.exe" config --global user.email "joseba.kayzen@gmail.com"
"C:\Program Files\Git\cmd\git.exe" add .
"C:\Program Files\Git\cmd\git.exe" commit -m "Initial commit: YouTube downloader with transcription and summary"
"C:\Program Files\Git\cmd\git.exe" remote add origin https://github.com/sepeto/YoutubeSummarizer.git
"C:\Program Files\Git\cmd\git.exe" branch -M main
"C:\Program Files\Git\cmd\git.exe" push -u origin main
pause 