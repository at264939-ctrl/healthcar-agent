@echo off
REM Run the Send to GitHub application

cd /d "%~dp0"

REM Activate virtual environment and run
call venv\Scripts\activate.bat
python main.py
pause
