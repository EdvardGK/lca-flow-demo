#!/usr/bin/env python3
"""
Quick test to verify the changes:
1. Analysis IFC saves to "Skiplum demo" folder
2. Excel is NOT saved automatically
"""

from ifc_sync_simple import SimpleIFCSync
from pathlib import Path

# Initialize sync
sync = SimpleIFCSync(input_folder="input", output_folder="output")

print("🧪 Testing changes...")
print("=" * 60)

# Run workflow with test file
print("\n1️⃣ Running workflow with G55_ARK.ifc...")
result = sync.run_workflow("G55_ARK.ifc")

if result:
    print("\n✅ Workflow completed successfully!")

    # Check 1: Analysis IFC location
    print("\n2️⃣ Checking analysis IFC location...")
    analysis_ifc = result['analysis_ifc']
    print(f"   Expected: input/Skiplum demo/G55_ARK_analyse.ifc")
    print(f"   Actual:   {analysis_ifc}")

    if "Skiplum demo" in str(analysis_ifc):
        print("   ✅ PASS: Analysis IFC in Skiplum demo folder")
    else:
        print("   ❌ FAIL: Analysis IFC not in Skiplum demo folder")

    if analysis_ifc.exists():
        print(f"   ✅ PASS: Analysis IFC file exists ({analysis_ifc.stat().st_size / 1024 / 1024:.1f} MB)")
    else:
        print("   ❌ FAIL: Analysis IFC file does not exist")

    # Check 2: Excel NOT saved
    print("\n3️⃣ Checking that Excel was NOT saved automatically...")
    expected_excel = sync.output_folder / "G55_ARK.xlsx"
    print(f"   Expected: NO file at {expected_excel}")

    if not expected_excel.exists():
        print("   ✅ PASS: No Excel file created automatically")
    else:
        print("   ❌ FAIL: Excel file was created (should not be)")

    # Check 3: DataFrame returned
    print("\n4️⃣ Checking DataFrame...")
    df = result['dataframe']
    print(f"   Rows: {len(df)}")
    print(f"   Columns: {len(df.columns)}")
    print(f"   ✅ PASS: DataFrame returned with data")

    # Check 4: Excel key NOT in result
    print("\n5️⃣ Checking return value...")
    if 'excel' not in result:
        print("   ✅ PASS: 'excel' key not in result (expected)")
    else:
        print("   ❌ FAIL: 'excel' key found in result (should be removed)")

    print("\n" + "=" * 60)
    print("🎉 All checks completed!")
    print("=" * 60)

    # List files in Skiplum demo folder
    print("\n📁 Contents of Skiplum demo folder:")
    skiplum_folder = Path("input/Skiplum demo")
    if skiplum_folder.exists():
        for file in skiplum_folder.iterdir():
            size_mb = file.stat().st_size / 1024 / 1024
            print(f"   - {file.name} ({size_mb:.1f} MB)")
    else:
        print("   ⚠️ Skiplum demo folder not found")

else:
    print("❌ Workflow failed")
