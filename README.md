Mother's Kitchen

Steps to install necessary software and run:
1) python -m venv venv
2) Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
3) .\venv\Scripts\Activate.ps1
4) python -m pip install --upgrade pip
5) python -m pip install -r .\requirements.txt
6) python .\app.py

To load the Demo data so proper graphs are visible:
1) # Ctrl+C to stop
2) python seed_demo_data.py
3) python .\app.py

This should load the test data
