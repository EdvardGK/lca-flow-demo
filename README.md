# IFC-Excel Sync POC
## Simple BIM LCA Workflow with Streamlit Dashboard

**Quick proof of concept for IFC → Excel → Analysis IFC sync workflow**

No Dalux dependency. Works with local files. Use with Solibri for visualization.

---

## 🎯 What It Does

1. **Extract**: IFC elements → Excel spreadsheet
2. **Enhance**: Creates analysis IFC copy with custom property sets (G55_Prosjektinfo, G55_LCA)
3. **Edit**: Modify LCA data in Excel (Gjenbruksstatus, CO2_kg, etc.)
4. **Sync**: Update analysis IFC with Excel edits
5. **Analyze**: Streamlit dashboard with LCA analytics and pivot tables

**Result**: Clean workflow from IFC model → Excel editing → Analysis IFC for Solibri

---

## 🚀 Quick Start

### 1. Install Dependencies

```bash
# Navigate to poc-sync folder
cd poc-sync

# Install requirements
pip install -r requirements.txt
```

### 2. Add Your IFC File

```bash
# Place your IFC file in the input folder
# (Create folder if it doesn't exist)
mkdir -p ../input
cp /path/to/your/model.ifc ../input/
```

### 3. Run Workflow

**Option A: Python Script** (headless)
```bash
python ifc_sync_simple.py your-model.ifc
```

**Option B: Streamlit Dashboard** (interactive)
```bash
streamlit run streamlit_dashboard.py
```

---

## 📁 Folder Structure

```
poc-sync/
├── ifc_sync_simple.py          # Core sync script
├── streamlit_dashboard.py      # Interactive dashboard
├── requirements.txt            # Dependencies
└── README.md                   # This file

../input/                       # Place IFC files here
../output/                      # Excel and analysis IFC output
```

---

## 🔄 Workflow Steps

### Step 1: Extract IFC to Excel

```python
from ifc_sync_simple import SimpleIFCSync

sync = SimpleIFCSync(input_folder="../input", output_folder="../output")
result = sync.run_workflow("your-model.ifc")

# Result contains:
# - result['excel']: Path to Excel file
# - result['analysis_ifc']: Path to analysis IFC
# - result['dataframe']: Pandas DataFrame with data
```

**Output:**
- `../output/your-model.xlsx` - Excel with all IFC element data
- `../output/your-model_analyse.ifc` - Analysis IFC copy

### Step 2: Edit Excel

Open `../output/your-model.xlsx` in Excel and edit:

**Key columns to modify:**
- `G55_LCA.Gjenbruksstatus` - Set to "NY", "EKS", or "GJEN"
- `G55_LCA.CO2_kg` - Add carbon footprint data
- `G55_LCA.LCA_Method` - Document calculation method
- `G55_LCA.Notes` - Add notes

### Step 3: Sync Back to IFC

```python
# After editing Excel, sync changes to analysis IFC
sync.sync_excel_to_ifc(
    excel_path=Path("../output/your-model.xlsx"),
    analysis_ifc_path=Path("../output/your-model_analyse.ifc")
)
```

### Step 4: Open in Solibri

Open `../output/your-model_analyse.ifc` in Solibri to view:
- Updated property sets
- G55_LCA properties
- Gjenbruksstatus categorization

---

## 📊 Streamlit Dashboard

The dashboard provides:

### 1. **Data View** Tab
- View all IFC element data
- Filter by entity type, material
- Search and explore properties
- Export filtered data

### 2. **LCA Analysis** Tab
- **Gauge charts** showing % of volume by MMI code
  - 🔴 NY (Nytt) - New elements
  - 🟡 EKS (Eksisterende) - Existing elements
  - 🟢 GJEN (Gjenbruk) - Reused elements
- **Material breakdown** - Volume by material type
- **Stacked bar charts** - Material × MMI status
- **Pivot tables** - Detailed analytics
- **CSV export** - Download pivot tables

### 3. **Edit Data** Tab
- Interactive data editor
- Edit cells directly
- Add/remove rows
- Save changes and sync to IFC

---

## 🏗️ Custom Property Sets

The analysis IFC includes these custom property sets:

### G55_Prosjektinfo
```
- Prosjekt: "Grønland 55"
- Opprettet: ISO timestamp
- Status: "Analyse"
```

### G55_LCA
```
- External_ID: GUID reference
- Basert_på_IFC: Source file + timestamp
- Gjenbruksstatus: "NY" | "EKS" | "GJEN"
- LCA_Status: "Pending" | "Complete"
- CO2_kg: Carbon footprint
- LCA_Method: Calculation method
- Notes: Free text
```

---

## 💡 Use Cases

### Scenario 1: Initial LCA Assessment
1. Extract IFC to Excel
2. Review elements and materials
3. Set Gjenbruksstatus based on project plans
4. Add CO2_kg estimates
5. Sync to analysis IFC
6. Open in Solibri for review

### Scenario 2: Iterative Updates
1. Load existing Excel file in dashboard
2. Edit LCA properties as project evolves
3. Sync changes to analysis IFC
4. Share updated analysis model with team

### Scenario 3: Reporting
1. Use LCA Analysis tab for quick insights
2. Generate pivot tables by material × MMI status
3. Export CSV for reporting
4. Screenshot gauge charts for presentations

---

## 🔧 Technical Details

### IFC Element Extraction

The script extracts:
- **Basic data**: GUID, BIM_ID, Entity, Name, Type, Material
- **All property sets**: Automatically flattens to Excel columns
- **Material relationships**: Multi-material elements handled
- **Metadata**: Source file, extraction timestamp

### Excel Format

Columns are formatted as: `PropertySet.PropertyName`

Example:
```
GUID | BIM_ID | Entity | Name | G55_LCA.Gjenbruksstatus | G55_LCA.CO2_kg
-----|--------|--------|------|-------------------------|----------------
abc  | 123    | IfcWall| Wall1| NY                      | 150.5
```

### Sync Logic

When syncing Excel → IFC:
1. Read Excel row by row
2. Match GUID to IFC element
3. Update/create property sets
4. Parse column names: `PsetName.PropertyName`
5. Save updated IFC

---

## 🎨 Dashboard Features

### Professional Visualizations
- **Gauge charts**: Instant visual feedback on sustainability metrics
- **Stacked bar charts**: Material composition by reuse status
- **Interactive filters**: Drill down into specific element types
- **Responsive layout**: Works on any screen size

### Data Quality
- **Automatic MMI detection**: Reads from existing property sets
- **Smart defaults**: Missing data handled gracefully
- **Volume estimation**: Uses available quantity data or defaults

### Export Options
- **CSV export**: Pivot tables for further analysis
- **Excel export**: Save edited data
- **Analysis IFC**: Updated model for Solibri

---

## 📋 Requirements

### Python Packages
```
ifcopenshell>=0.7.0
pandas>=2.0.0
openpyxl>=3.1.0
streamlit>=1.28.0
plotly>=5.18.0
```

### System Requirements
- Python 3.8+
- 4GB RAM (8GB+ for large models)
- Web browser (for Streamlit dashboard)

---

## 🚨 Known Limitations

1. **Volume data**: If IFC doesn't have volume properties, uses placeholder values
2. **MMI detection**: Searches common property sets - may need customization
3. **Large files**: Models >500MB may be slow - consider splitting
4. **Material extraction**: Multi-layer materials shown as pipe-separated list

---

## 🔮 Future Enhancements

- [ ] Automatic volume calculation from geometry
- [ ] CO2 database integration
- [ ] Multi-file batch processing
- [ ] Change tracking between syncs
- [ ] Direct Solibri integration via BCF
- [ ] PDF report generation

---

## 📞 Support

For issues or questions:
1. Check the logs for error messages
2. Verify IFC file is valid (open in Solibri first)
3. Ensure all dependencies are installed
4. Review this README

---

## 📄 License

Internal use - Spruce Forge Development

---

## 🏁 Quick Reference

```bash
# Full workflow in 4 commands

# 1. Install
pip install -r requirements.txt

# 2. Run extraction
python ifc_sync_simple.py model.ifc

# 3. Edit Excel
open ../output/model.xlsx

# 4. Launch dashboard for sync + analysis
streamlit run streamlit_dashboard.py
```

**That's it!** Simple workflow, powerful results. 🎉
