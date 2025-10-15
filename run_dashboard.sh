#!/bin/bash
# Quick launcher for Streamlit dashboard
# Run: chmod +x run_dashboard.sh && ./run_dashboard.sh

echo "Starting BIM LCA Dashboard..."
echo ""

# Check if streamlit is installed
if ! python -c "import streamlit" 2>/dev/null; then
    echo "ERROR: Streamlit not installed!"
    echo ""
    echo "Installing dependencies..."
    pip install -r requirements.txt
    echo ""
fi

# Launch dashboard
echo "Opening dashboard in browser..."
streamlit run streamlit_dashboard.py
