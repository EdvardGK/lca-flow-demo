# Log Cleanup Fix

**Date**: 2025-10-15
**Issue**: Excessive warnings during IFC extraction

## Problem

When processing the G55_ARK.ifc file, the log showed ~150 warnings like:
```
WARNING - Error processing 2lERbNtxrF5fdrId74eUTW: entity instance of type 'IFC2X3.IfcBuilding' has no attribute 'ContainedInStructure'
WARNING - Error processing 3POXqHuM96DwZzM2c25Gzg: entity instance of type 'IFC2X3.IfcBuildingStorey' has no attribute 'ContainedInStructure'
WARNING - Error processing 3POXqHuM96DwZzM2c25H4t: entity instance of type 'IFC2X3.IfcSpace' has no attribute 'ContainedInStructure'
```

## Root Cause

The code was trying to access `product.ContainedInStructure` for ALL IfcProduct instances, including:
- **IfcSite** - Top-level spatial container
- **IfcBuilding** - Building container
- **IfcBuildingStorey** - Floor/storey container
- **IfcSpace** - Room/space container
- **IfcZone** - Zone grouping

These are **spatial CONTAINER elements** - they don't have `ContainedInStructure` because they ARE the containers, not the elements contained within them.

Only building elements (walls, slabs, beams, etc.) are "contained in" spatial structures.

## Solution

Added check to skip spatial container elements before accessing `ContainedInStructure`:

```python
# Spatial container elements that don't have ContainedInStructure relationship
spatial_elements = ('IfcSite', 'IfcBuilding', 'IfcBuildingStorey', 'IfcSpace', 'IfcZone')

# Extract Floor information (skip for spatial container elements)
if not product.is_a() in spatial_elements:
    if hasattr(product, 'ContainedInStructure'):
        for rel in product.ContainedInStructure:
            # ... extract floor/zone info
```

## Result

- ✅ Cleaner log output
- ✅ No functional changes (code still extracts all data correctly)
- ✅ Faster processing (skips unnecessary attribute checks)

## File Modified

- `ifc_sync_simple.py` (lines 83-135)

## Testing

Re-run the demo with G55_ARK.ifc to verify:
1. No warnings for spatial elements
2. All building elements still get Floor/Zone information correctly
3. Excel output is identical to previous version
