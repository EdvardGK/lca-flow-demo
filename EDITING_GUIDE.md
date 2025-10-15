# Gjenbruksstatus Editing Guide

## Overview

The LCA Flow Demo now includes a powerful interface for editing Gjenbruksstatus (reuse status) values for BIM elements. This is perfect for demonstrations and real-world LCA analysis.

## What is Gjenbruksstatus?

Gjenbruksstatus categorizes building elements by their sustainability status:

- **NY** - Nytt (New) - Brand new elements/materials
- **EKS** - Eksisterende (Existing) - Elements that already exist in the building
- **GJEN** - Gjenbruk (Reuse) - Elements that are reused from other projects

This information is stored in the `G55_LCA.Gjenbruksstatus` property in the IFC file.

## Where It's Used

### 1. IFC Extraction
When you extract an IFC file:
- The `G55_LCA.Gjenbruksstatus` property is automatically created with default value "NY"
- Existing values are preserved if they already exist in the IFC
- MMI codes (300/700/800) are automatically mapped to NY/EKS/GJEN if found

### 2. LCA Analysis Tab
The gauge charts and visualizations show:
- % of volume that is NY (red)
- % of volume that is EKS (yellow)
- % of volume that is GJEN (green)
- Material breakdowns by status

### 3. Edit Data Tab
Two editing modes are available:

## Editing Modes

### 🎯 Rask redigering (Quick Edit)

**Perfect for demos and bulk changes!**

**Features:**
- Filter elements by type (IfcWall, IfcSlab, etc.)
- Filter by material (Concrete, Steel, etc.)
- See current distribution (how many NY/EKS/GJEN)
- Select new status from dropdown
- Update ALL filtered elements with one click
- Instant preview of changes

**Demo Workflow:**
1. Go to "✏️ Rediger data" tab
2. Click "🎯 Rask redigering" sub-tab
3. Select filter (e.g., "IfcWall")
4. See current distribution of wall elements
5. Choose new status (e.g., "GJEN")
6. Click "✅ Oppdater valgte elementer"
7. Switch to "📈 LCA-analyse" tab to see updated gauges!

**Example Demo Scenario:**
```
"Let's say we're reusing all the concrete walls from an old building..."

1. Filter: Entity = "IfcWall"
2. Filter: Material = "Concrete"
3. Shows: 145 elements, currently 145 NY, 0 GJEN
4. Select: "GJEN" from dropdown
5. Click: "Oppdater valgte elementer"
6. Result: Now shows 0 NY, 145 GJEN
7. Go to LCA Analysis → gauge shows increased GJEN %!
```

### 📋 Avansert redigering (Advanced Edit)

**For detailed, row-by-row editing**

**Features:**
- Full spreadsheet-like editor
- Edit any column in the dataset
- Dropdown for Gjenbruksstatus column
- Add/delete rows (dynamic)
- Edit all properties including CO2_kg, notes, etc.

**When to use:**
- Making specific changes to individual elements
- Editing multiple properties at once
- Advanced users who need full control

## Data Flow

```
IFC File
  ↓
[Extract] → Creates G55_LCA.Gjenbruksstatus (default: NY)
  ↓
Excel/DataFrame
  ↓
[Edit in Dashboard] → Change values (NY/EKS/GJEN)
  ↓
[Save Changes] → Updates session state + Excel file
  ↓
[Sync to IFC] → Writes back to analysis IFC
  ↓
[LCA Analysis] → Gauge charts update in real-time
```

## Technical Details

### Property Mapping

The system looks for Gjenbruksstatus in this order:
1. `G55_LCA.Gjenbruksstatus` (primary)
2. Any column with "MMI" in the name
3. Defaults to "NY" if not found

### MMI Code Mapping

If MMI codes are found, they're mapped automatically:
- MMI 300 → NY
- MMI 700 → EKS
- MMI 800 → GJEN

### Display vs Storage

- **Storage:** NY, EKS, GJEN (short codes)
- **Display:** NY (Nytt), EKS (Eksisterende), GJEN (Gjenbruk)

### Updates are Atomic

When you click "Oppdater valgte elementer":
1. DataFrame is updated in memory
2. Session state is updated
3. Excel file is overwritten (if it exists)
4. UI refreshes to show changes
5. Changes are ready to sync to IFC

## Best Practices

### For Demos

1. **Start fresh** - Extract IFC to get all elements as "NY"
2. **Show the problem** - LCA Analysis shows 100% new materials (bad!)
3. **Make it better** - Go to Edit tab, change walls to "GJEN"
4. **Show impact** - LCA Analysis now shows improved sustainability
5. **Sync to IFC** - Export updated analysis model

### For Real Projects

1. **Extract once** - Get IFC data into Excel
2. **Analyze by type** - Use filters to group similar elements
3. **Consult experts** - Work with sustainability team on status
4. **Batch update** - Use quick edit for large groups
5. **Fine-tune** - Use advanced edit for specific elements
6. **Iterate** - Make changes, review LCA analysis, repeat
7. **Sync regularly** - Keep IFC model in sync with decisions

## Common Workflows

### Scenario 1: Existing Building Renovation

```
Goal: Mark existing structure as EKS, new additions as NY

1. Filter: Entity = "IfcColumn"
2. Status: EKS (existing columns stay)
3. Filter: Entity = "IfcWall", Material = "New walls"
4. Status: NY (new walls)
```

### Scenario 2: Maximum Reuse Project

```
Goal: Identify opportunities for material reuse

1. Filter: Material = "Steel"
2. Review elements that could be reused
3. Status: GJEN for reusable steel
4. Repeat for other materials
5. LCA Analysis shows reuse %
```

### Scenario 3: Quick Demo

```
Goal: Show dramatic improvement in 30 seconds

1. Start: 100% NY (red gauge at 100%)
2. Filter: Material = "Concrete"
3. Change to: GJEN
4. Result: Green gauge jumps to 60%!
5. Message: "Look how much better we can do!"
```

## Validation

The system validates Gjenbruksstatus values:
- Only accepts: NY, EKS, GJEN
- Invalid values default to NY
- Empty/null values default to NY
- Case-insensitive (ny → NY)

## Syncing Changes

After editing, changes exist in:
1. Session state (temporary)
2. Excel file (persistent)

To update the IFC file:
1. Go to sidebar
2. Find "🔄 Synkroniser til IFC" section
3. Click "💾 Synkroniser Excel → IFC"
4. Analysis IFC is updated with new values
5. Open in Solibri to verify

## Keyboard Shortcuts

In Advanced Edit mode:
- **Tab** - Move to next cell
- **Enter** - Move down
- **Arrow keys** - Navigate
- **Click dropdown** - Select status
- **Delete** - Clear cell

## Performance Notes

- Quick Edit: Instant for any number of filtered elements
- Advanced Edit: Best for < 10,000 rows
- Large files: Use filters to reduce displayed rows

## Troubleshooting

### "Gjenbruksstatus column missing"

**Cause:** IFC was extracted before G55_LCA was added
**Solution:** Re-extract IFC or column is auto-created with defaults

### Changes don't show in LCA Analysis

**Cause:** Changes not saved
**Solution:** Click save button before switching tabs

### Sync fails

**Cause:** Excel file doesn't match IFC structure
**Solution:** Re-extract IFC to start fresh

### All elements show as NY

**Cause:** Default values not yet changed
**Solution:** This is expected! Use Edit tab to change values

## Future Enhancements

Potential improvements:
- [ ] Multi-select for status (select multiple entities at once)
- [ ] Undo/redo functionality
- [ ] Change history log
- [ ] Import status from CSV
- [ ] AI suggestions based on element type
- [ ] Comparison with industry benchmarks

## Integration with Other Tools

### Solibri

After syncing to IFC:
1. Open `*_analyse.ifc` in Solibri
2. View G55_LCA property set
3. Filter/color-code by Gjenbruksstatus
4. Create BCF issues for review

### Excel

The Excel file can be edited externally:
1. Download Excel from dashboard
2. Edit in Microsoft Excel
3. Upload back to dashboard
4. Sync to IFC

### Revit/ArchiCAD

Future: Direct integration to read/write Gjenbruksstatus in BIM authoring tools

## Code Reference

Key functions:
- `extract_gjenbruksstatus()` - Extracts status from IFC data (line 117)
- `map_mmi_to_status()` - Maps MMI codes (line 136)
- `map_status_to_display()` - Maps to display names (line 156)

Key files:
- `streamlit_dashboard.py` (lines 668-832) - Edit interface
- `ifc_sync_simple.py` (lines 137-217) - IFC property creation
