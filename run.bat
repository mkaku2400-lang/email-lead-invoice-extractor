@echo off
rem One-click start for Windows: sets up on first run, then opens the dashboard.
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
    echo First run: creating the Python environment and installing libraries...
    python -m venv .venv || goto :error
    ".venv\Scripts\python.exe" -m pip install --disable-pip-version-check -r requirements.txt || goto :error
)

".venv\Scripts\python.exe" -m streamlit run app.py
goto :eof

:error
echo.
echo Setup failed. Check that Python 3.10 or newer is installed and you are online.
pause
