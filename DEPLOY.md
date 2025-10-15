# Streamlit Cloud Deployment Guide

## Quick Deploy to Streamlit Cloud

### 1. Push to GitHub
Make sure your repository is pushed to GitHub:
```bash
git remote add origin https://github.com/EdvardGK/lca-flow-demo.git
git branch -M main
git add .
git commit -m "Ready for Streamlit Cloud deployment"
git push -u origin main
```

### 2. Deploy on Streamlit Cloud

1. Go to [share.streamlit.io](https://share.streamlit.io)
2. Sign in with GitHub
3. Click "New app"
4. Select:
   - **Repository:** `EdvardGK/lca-flow-demo`
   - **Branch:** `main`
   - **Main file path:** `streamlit_dashboard.py`
5. Click "Deploy!"

### 3. App Configuration

Create `.streamlit/config.toml` (optional, for customization):

```toml
[theme]
primaryColor = "#2E7D32"
backgroundColor = "#FFFFFF"
secondaryBackgroundColor = "#F0F2F6"
textColor = "#262730"
font = "sans serif"

[server]
maxUploadSize = 500
enableCORS = false
```

### 4. Dependencies

All dependencies are in `requirements.txt`:
- ifcopenshell
- pandas
- openpyxl
- streamlit
- plotly
- altair

Streamlit Cloud will automatically install these.

## App Usage (Cloud Version)

### For Demo Presenters:

1. **Upload IFC File:**
   - Click "Browse files" in sidebar
   - Select your IFC file (drag & drop works too)
   - File uploads to cloud temporarily

2. **Extract & Analyze:**
   - Click "🔄 Extract Uploaded IFC"
   - View analytics in "📈 LCA Analysis" tab
   - Show gauge charts and material breakdowns

3. **Edit Data:**
   - Go to "✏️ Edit Data" tab
   - Make live edits during demo
   - Click "💾 Save Changes & Update Excel"

4. **Download Results:**
   - Sidebar → "📥 Download Files"
   - Download Excel spreadsheet
   - Download Analysis IFC for Solibri

### File Size Limits

Streamlit Cloud free tier:
- Max upload: 200MB per file
- For larger files, consider upgrading or using local deployment

## Local Testing Before Deploy

```bash
# Run locally to test before deploying
streamlit run streamlit_dashboard.py

# Open in browser at http://localhost:8501
```

## Troubleshooting

### ifcopenshell Installation Issues
If deployment fails due to ifcopenshell:
- It should work automatically on Streamlit Cloud
- If issues persist, contact Streamlit support

### Upload Issues
- Check file size < 200MB
- Ensure `.ifc` extension
- Try different browser if drag & drop fails

### Performance
- Large IFC files (>100MB) may take longer to process
- Consider showing progress spinner during demo
- Pre-process files locally for faster demo experience

## Demo Tips

1. **Pre-upload a sample IFC** before presentation starts
2. **Show the workflow** step by step (upload → extract → edit → sync → download)
3. **Highlight the gauge charts** - they're visually impressive
4. **Demonstrate live editing** - change Gjenbruksstatus values in real-time
5. **Emphasize cloud accessibility** - "works on any computer, no installation"

## Security Notes

- Uploaded files are stored temporarily in cloud
- Files are deleted when session ends
- Don't upload sensitive/proprietary IFC files on free tier
- For production use, consider private deployment

## Next Steps After Demo

If the demo is successful:
1. Add authentication (Streamlit supports Google/GitHub OAuth)
2. Set up persistent storage (S3, Azure Blob)
3. Add batch processing for multiple files
4. Integrate with CO2 databases for automatic calculations
5. Deploy to private cloud for proprietary data

---

**App URL:** Will be something like `https://edvardgk-lca-flow-demo-streamlit-dashboard-abc123.streamlit.app/`

Share this URL with your audience for live demo!
