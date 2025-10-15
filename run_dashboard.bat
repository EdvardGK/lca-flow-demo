@echo off
REM Quick launcher for Streamlit dashboard
REM Double-click this file to start the dashboard

echo Starting BIM LCA Dashboard...
echo.

REM Check if streamlit is installed
python -c "import streamlit" 2>NUL
if errorlevel 1 (
    echo ERROR: Streamlit not installed!
    echo.
    echo Installing dependencies...
    pip install -r requirements.txt
    echo.
)

REM Launch dashboard
echo Opening dashboard in browser...
streamlit run streamlit_dashboard.py

pause
