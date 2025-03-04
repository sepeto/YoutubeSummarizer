@echo off
"C:\Program Files\Git\cmd\git.exe" init
"C:\Program Files\Git\cmd\git.exe" add .
"C:\Program Files\Git\cmd\git.exe" commit -m "Initial commit"
"C:\Program Files\Git\cmd\git.exe" remote add origin https://github.com/sepeto/YoutubeSummarizer.git
"C:\Program Files\Git\cmd\git.exe" push -u origin main
pause 