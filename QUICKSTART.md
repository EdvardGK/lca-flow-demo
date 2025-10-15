# Quick Start Guide
## Get Running in 5 Minutes

---

## Step 1: Install Dependencies (1 minute)

Open terminal in `poc-sync` folder:

```bash
pip install -r requirements.txt
```

---

## Step 2: Add IFC File (30 seconds)

Place your IFC file in the `../input/` folder:

```bash
# Windows
copy "C:\path\to\your\model.ifc" ..\input\

# Mac/Linux
cp /path/to/your/model.ifc ../input/
```

---

## Step 3: Launch Dashboard (30 seconds)

```bash
streamlit run streamlit_dashboard.py
```

**Dashboard opens in browser automatically** at http://localhost:8501

---

## Step 4: Extract IFC (1 minute)

1. **Select your IFC file** from dropdown in sidebar
2. Click **"🔄 Extract IFC to Excel"** button
3. Wait for extraction to complete
4. ✅ Done! Excel and analysis IFC created in `../output/`

---

## Step 5: View LCA Analysis (30 seconds)

1. Click **"📈 LCA Analysis"** tab
2. See gauge charts showing:
   - 🔴 % NYTT (new)
   - 🟡 % EKSISTERENDE (existing)
   - 🟢 % GJENBRUK (reuse)
3. Scroll down for material breakdown

---

## Step 6: Edit Data (optional)

**In Excel:**
1. Open `../output/your-model.xlsx`
2. Edit LCA columns (Gjenbruksstatus, CO2_kg, etc.)
3. Save Excel

**In Dashboard:**
1. Click **"📂 Load Excel"** in sidebar
2. Go to **"✏️ Edit Data"** tab
3. Edit directly in browser
4. Click **"💾 Save Changes"**

---

## Step 7: Sync to IFC (30 seconds)

1. In sidebar, see **"🔄 Sync to IFC"** section
2. Click **"💾 Sync Excel → IFC"** button
3. ✅ Analysis IFC updated!

---

## Step 8: Open in Solibri

```bash
# Open analysis IFC in Solibri
open ../output/your-model_analyse.ifc
```

Check the new property sets:
- `G55_Prosjektinfo`
- `G55_LCA`

---

## Troubleshooting

### Dashboard won't start
```bash
# Make sure streamlit is installed
pip install streamlit

# Run from poc-sync folder
cd poc-sync
streamlit run streamlit_dashboard.py
```

### No IFC files found
```bash
# Check input folder exists
ls ../input/

# If not, create it
mkdir ../input
```

### Import error: "No module named ifcopenshell"
```bash
# Install ifcopenshell
pip install ifcopenshell
```

### Python script mode (no dashboard)
```bash
# Run headless extraction
python ifc_sync_simple.py your-model.ifc
```

---

## What's Next?

- **Iterate**: Edit Excel → Sync → Review in Solibri
- **Analyze**: Use LCA Analysis tab for insights
- **Export**: Download pivot tables as CSV
- **Share**: Send analysis IFC to team

---

## Pro Tips

1. **Batch processing**: Drop multiple IFC files in `input/`, extract one by one
2. **Version control**: Excel files are timestamped - keep history
3. **Custom properties**: Add any property in Excel as `PsetName.PropertyName`
4. **Material filtering**: Use Data View filters to focus on specific materials
5. **Quick edits**: Use dashboard Edit tab for small changes, Excel for bulk edits

---

**That's it! You're up and running.** 🚀

For detailed documentation, see [README.md](README.md)
