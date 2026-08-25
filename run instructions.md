# Run Instructions

cd ~/Downloads/EmergencyWaitlistMatchingSystem_Local
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
python -m py_compile app.py
python -m streamlit run app.py

Open http://localhost:8501
