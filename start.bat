@echo off
echo Starting Flight Tracker Server...
start /min wsl.exe -d Ubuntu --cd ~ -e bash -lic "cd ~/github/Flight-Tracker && { [ -d .venv ] || { python3 -m venv .venv && ./.venv/bin/pip install -q -r requirements.txt; }; } && ./.venv/bin/python processor.py"
timeout /t 4 /nobreak > NUL
start http://localhost:5000
