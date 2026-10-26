V2X Overtake Risk Engine - Satvik Gupta, Project 2627S761

Run on your laptop:
1. Install Python from python.org (tick "Add Python to PATH").
2. Open this folder, double-click run_windows.bat  (Mac: open Terminal here, run:
   pip3 install -r requirements.txt  then  streamlit run app.py)
3. The browser opens the app at http://localhost:8501

Files:
app.py          the web app (Streamlit): 3 tabs
simulator.py    road simulator: cars, signal, pedestrian, ambulance, V2X messages
risk_engine.py  the overtake rules + 15 tests (python risk_engine.py)
index.html      spare demo: double-click, works without internet or Python
