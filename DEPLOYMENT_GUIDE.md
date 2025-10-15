# LCA Flow Demo - Deployment Guide

**Date**: 2025-10-15
**Supports**: Local deployment + Streamlit Cloud

---

## 🌍 Two Deployment Modes

The app **auto-detects** the environment and adapts its behavior:

### 💻 **Local Mode** (Full Power)
- Run on your machine: `streamlit run streamlit_dashboard.py`
- Files saved to `input/` and `output/` folders
- **Solibri integration works!** (file watcher detects changes)
- Real-time updates between Streamlit and Solibri

### ☁️ **Cloud Mode** (Streamlit Cloud)
- Deploy to Streamlit Community Cloud
- Files in temporary directory (ephemeral)
- **No Solibri integration** (files on remote server)
- Download analysis IFC to use locally

---

## 📋 What You Need to Consider

### For Streamlit Cloud Deployment

#### ✅ **Works Great:**
- Upload IFC files via browser
- View LCA analysis and gauges
- Use scenario buttons to test different strategies
- Download updated analysis IFC
- Download Excel export
- Share demo link with clients

#### ⚠️ **Limitations:**
- **No Solibri live integration** (files are on cloud server, not your PC)
- Files deleted after session ends (download to keep)
- Uploaded files limited to Streamlit Cloud file size limits (~200MB)
- Processing large IFC files may be slower (cloud resources)

#### 💡 **Workaround for Solibri:**
1. User uploads IFC on Streamlit Cloud
2. User makes changes (scenario buttons)
3. User downloads analysis IFC
4. User opens downloaded IFC in Solibri locally

**This works, but isn't "live" - user must re-download after each change**

---

## 🚀 Deployment Scenarios

### Scenario A: Demo for Clients (Cloud)

**Best for:**
- Showing LCA concept to clients
- Letting clients try scenarios themselves
- Public demos at conferences
- Sharing link via email

**Workflow:**
```
1. Deploy to Streamlit Cloud
2. Share link: https://your-app.streamlit.app
3. Client uploads their IFC
4. Client clicks scenario buttons
5. Client sees gauge charts update
6. Client downloads analysis IFC for their BIM tool
```

**Limitations:**
- No live Solibri integration
- Files temporary (30min-1hr session)

---

### Scenario B: Live Presentation (Local + Projector)

**Best for:**
- Live presentations with Solibri on screen
- Workshops where you control both apps
- Internal demos with full integration

**Setup:**
```
1. Run locally: streamlit run streamlit_dashboard.py
2. Open IFC in Solibri (from output/ folder)
3. Project Streamlit on one screen, Solibri on another
4. Click scenario in Streamlit → Solibri prompts to reload!
```

**Benefits:**
- ✅ Live updates
- ✅ Instant visual feedback
- ✅ "Wow factor" for audience

---

### Scenario C: Hybrid (Cloud Demo + Local Solibri)

**Best for:**
- Remote presentations
- Client can't install Streamlit locally
- You want to show Solibri integration

**Workflow:**
```
1. Client accesses Streamlit Cloud demo
2. You have Solibri open locally with same IFC
3. Client makes changes on cloud
4. Client downloads updated IFC
5. You load it in Solibri and show results
```

**Note:** Not truly "live" but works for demos

---

## 🔧 Configuration

### Auto-Detection (Default)

The app automatically detects the environment:

```python
# In streamlit_dashboard.py
def is_cloud_deployment():
    """Detect if running on Streamlit Cloud"""
    return os.getenv('STREAMLIT_SHARING_MODE') is not None or \
           os.getenv('STREAMLIT_SERVER_HEADLESS') == 'true'
```

**Cloud indicators:**
- Temp directory used for files
- Warning message: "☁️ Cloud Mode: Download analysis IFC to use with Solibri"
- Download buttons emphasized

**Local indicators:**
- `input/` and `output/` folders used
- Success message: "💻 Local Mode: Solibri can watch analysis IFC"
- Solibri integration messages shown

### Manual Override (If Needed)

Force cloud mode even when running locally:

```python
# In streamlit_dashboard.py, change line 80:
use_temp = True  # Force temp directory
```

Force local mode even on cloud (not recommended):

```python
use_temp = False  # Force local folders
```

---

## 📦 Streamlit Cloud Setup

### 1. Requirements File

**`requirements.txt`:**
```txt
streamlit>=1.28.0
pandas>=2.0.0
openpyxl>=3.1.0
plotly>=5.18.0
ifcopenshell>=0.7.0
```

### 2. App Configuration

**`.streamlit/config.toml`:**
```toml
[server]
maxUploadSize = 500  # Allow up to 500MB IFC files

[theme]
primaryColor = "#2E7D32"
backgroundColor = "#FFFFFF"
secondaryBackgroundColor = "#F0F2F6"
textColor = "#262730"
font = "sans serif"
```

### 3. Deploy to Streamlit Cloud

1. **Push to GitHub:**
   ```bash
   git add .
   git commit -m "Deploy LCA Flow Demo"
   git push origin main
   ```

2. **Connect on Streamlit Cloud:**
   - Go to https://share.streamlit.io
   - Click "New app"
   - Select your repo
   - Main file: `streamlit_dashboard.py`
   - Click "Deploy"

3. **Share link:**
   - `https://your-username-lca-flow-demo.streamlit.app`

---

## 💾 File Management

### Local Deployment

**Directory structure:**
```
lca-flow-demo/
├── input/              # Upload IFC files here (or via UI)
│   └── G55_ARK.ifc
├── output/             # Analysis IFC and Excel created here
│   ├── G55_ARK_analyse.ifc  ← Solibri watches this!
│   └── G55_ARK.xlsx
├── streamlit_dashboard.py
└── ifc_sync_simple.py
```

**Workflow:**
1. User uploads IFC → Saved to `input/`
2. Analysis IFC created → `output/{name}_analyse.ifc`
3. User edits → `output/{name}_analyse.ifc` updated in place
4. Solibri detects change → Prompts to reload

### Cloud Deployment

**Directory structure (temporary):**
```
/tmp/lca_demo_XXXXX/    # Random temp directory
├── input/
│   └── uploaded_file.ifc
└── output/
    ├── uploaded_file_analyse.ifc
    └── uploaded_file.xlsx
```

**Lifecycle:**
- Created when first IFC uploaded
- Persists during user session (~30min-1hr)
- Deleted when session ends or server restarts
- Users must download files to keep them

**Download strategy:**
- Analysis IFC: Generated in temp folder, served via download button
- Excel: Generated on-demand from DataFrame

---

## 🧪 Testing Before Deployment

### Local Testing (Simulate Cloud)

Force cloud mode to test behavior:

```python
# In streamlit_dashboard.py
use_temp = True  # Test cloud mode locally
```

Then run:
```bash
streamlit run streamlit_dashboard.py
```

**Verify:**
- [ ] Sidebar shows "☁️ Cloud Mode"
- [ ] Files go to temp directory
- [ ] Download buttons work
- [ ] No "Solibri will reload" messages
- [ ] App doesn't crash if output/ folder doesn't exist

### Streamlit Cloud Testing

After deployment:

**Test checklist:**
- [ ] Upload 50MB IFC → succeeds
- [ ] Upload 200MB IFC → succeeds (if under maxUploadSize)
- [ ] Scenario buttons work
- [ ] Gauges update correctly
- [ ] Download analysis IFC works
- [ ] Download Excel works
- [ ] Second upload works (replaces previous)
- [ ] Multiple tabs/users don't conflict

---

## 🐛 Troubleshooting

### Issue: "Output folder not found" on Cloud

**Problem:** App tries to use local `output/` folder

**Solution:** Ensure auto-detection is working:
```python
# Check this line exists in streamlit_dashboard.py
use_temp = is_cloud_deployment()
```

### Issue: Files disappear after refresh

**Expected behavior on Cloud** - files are in temp directory

**Solution:** Add download instructions:
```python
st.warning("💾 Download files before leaving - session files are temporary")
```

### Issue: Solibri integration doesn't work on Cloud

**This is expected!** Solibri is on user's local machine, files are on cloud server.

**Solution:** Show clear message:
```python
if st.session_state.is_cloud:
    st.info("Download analysis IFC to use with Solibri locally")
```

### Issue: Large IFC files timeout

**Problem:** Cloud has processing time limits

**Solution 1:** Increase timeout in `config.toml`:
```toml
[server]
enableCORS = false
enableXsrfProtection = false
maxMessageSize = 500
```

**Solution 2:** Add progress indicators:
```python
with st.spinner("Processing large file... this may take 30-60 seconds"):
    # Process IFC
```

### Issue: Multiple users interfere with each other

**Problem:** Session state collision

**Solution:** Streamlit Cloud handles this automatically via session isolation. Each user gets their own session. No action needed.

---

## 📊 Performance Considerations

### Local Deployment
- ✅ Fast (local filesystem)
- ✅ No file size limits
- ✅ Can process huge IFC files (10k+ elements)
- ✅ Solibri integration smooth

### Cloud Deployment
- ⚠️ Slower (network upload + processing)
- ⚠️ File size limits (default 200MB)
- ⚠️ Processing time limits (~10min)
- ❌ No Solibri integration

**Optimization tips:**
1. Use smaller test IFC files for cloud demos
2. Add progress bars for user feedback
3. Consider batch processing limits
4. Cache expensive operations with `@st.cache_data`

---

## 🎯 Recommendations

### For Your Use Case

Based on "launching on Streamlit Cloud":

**If you need Solibri integration:**
- ❌ **Don't use Streamlit Cloud** for live demos
- ✅ **Use local deployment** with projector/screen share
- ✅ Upload to cloud as "try it yourself" demo (no Solibri)

**If you don't need Solibri:**
- ✅ **Streamlit Cloud is perfect!**
- Users can upload, test scenarios, download results
- Share link via email for remote demos

### Best of Both Worlds

**Recommended setup:**

1. **Deploy to Streamlit Cloud:**
   - Use for client self-service demos
   - Share link: "Try our LCA tool: https://..."
   - No Solibri integration needed

2. **Keep local version:**
   - Use for live presentations
   - Show Solibri integration for "wow factor"
   - Run on your laptop during pitches

**This gives you:**
- ✅ Easy client access (cloud)
- ✅ Full power for presentations (local)
- ✅ Flexibility for different scenarios

---

## 🚀 Next Steps

1. **Test locally first:**
   ```bash
   streamlit run streamlit_dashboard.py
   ```

2. **Test cloud simulation:**
   ```python
   # Set use_temp = True in streamlit_dashboard.py
   ```

3. **Deploy to Streamlit Cloud:**
   - Push to GitHub
   - Connect on share.streamlit.io
   - Test with real IFC files

4. **Document for users:**
   - Add README with deployment instructions
   - Explain cloud vs local modes
   - Provide Solibri integration guide

---

## 📝 Summary

| Feature | Local Mode | Cloud Mode |
|---------|-----------|-----------|
| **File Upload** | ✅ Browser or folder | ✅ Browser only |
| **Processing Speed** | ⚡ Fast | 🐢 Slower |
| **File Persistence** | ✅ Permanent | ❌ Temporary |
| **Solibri Integration** | ✅ Live updates | ❌ Download required |
| **File Size Limit** | ✅ Unlimited | ⚠️ ~200MB |
| **Deployment** | 💻 Local only | 🌍 Public URL |
| **Best For** | Presentations | Self-service demos |

**Bottom line:** The app adapts automatically, but **Solibri integration only works locally**. For cloud deployment, users must download the analysis IFC to use in Solibri.
