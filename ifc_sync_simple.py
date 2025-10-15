#!/usr/bin/env python3
"""
Simple IFC-Excel Sync - Proof of Concept
=========================================
Workflow:
1. Extract IFC elements to Excel
2. Create analysis IFC copy ("filename_analyse.ifc")
3. Edit Excel and sync back to analysis IFC

No Dalux dependency - works with local files
"""

import ifcopenshell
import ifcopenshell.util.element
import ifcopenshell.api
import pandas as pd
from datetime import datetime
from pathlib import Path
from typing import Optional
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class SimpleIFCSync:
    """Simplified IFC-Excel sync for proof of concept"""

    def __init__(self, input_folder: str = "input", output_folder: str = "output"):
        """Initialize with input/output folders"""
        self.input_folder = Path(input_folder)
        self.output_folder = Path(output_folder)

        # Create folders if they don't exist
        self.input_folder.mkdir(exist_ok=True)
        self.output_folder.mkdir(exist_ok=True)

        logger.info(f"Input folder: {self.input_folder}")
        logger.info(f"Output folder: {self.output_folder}")

    def get_bim_id(self, element: ifcopenshell.entity_instance) -> Optional[str]:
        """Extract BIM authoring tool ID (e.g., Revit Element ID)"""
        if hasattr(element, 'Tag') and element.Tag:
            return str(element.Tag)

        psets = ifcopenshell.util.element.get_psets(element)
        for pset_name, props in psets.items():
            for prop_name, value in props.items():
                if any(id_name in prop_name.upper() for id_name in ['ELEMENTID', 'REVITID', 'BATID']):
                    if value:
                        return str(value)
        return None

    def extract_ifc_to_excel(self, ifc_path: Path) -> pd.DataFrame:
        """
        Extract IFC elements to Excel DataFrame

        Returns DataFrame with:
        - GUID (External ID for Solibri)
        - BIM_ID (Element ID from authoring tool)
        - Entity type
        - Name, Type, Material
        - All properties from custom property sets
        """
        logger.info(f"📖 Extracting IFC: {ifc_path.name}")

        ifc = ifcopenshell.open(str(ifc_path))
        products = ifc.by_type("IfcProduct")

        logger.info(f"Found {len(products)} products")

        data = []
        for product in products:
            try:
                # Basic element info
                row = {
                    'GUID': product.GlobalId,
                    'BIM_ID': self.get_bim_id(product),
                    'Entity': product.is_a(),
                    'Name': product.Name if hasattr(product, 'Name') else None,
                    'Type': product.ObjectType if hasattr(product, 'ObjectType') else None,
                }

                # Material extraction
                materials = ifcopenshell.util.element.get_materials(product)
                if materials:
                    material_names = [mat.Name for mat in materials if hasattr(mat, 'Name')]
                    row['Material'] = ' | '.join(material_names) if material_names else None
                else:
                    row['Material'] = None

                # Extract all property sets
                psets = ifcopenshell.util.element.get_psets(product)
                for pset_name, props in psets.items():
                    for prop_name, value in props.items():
                        col_name = f"{pset_name}.{prop_name}"
                        row[col_name] = value if value is not None else ""

                data.append(row)

            except Exception as e:
                logger.warning(f"Error processing {product.GlobalId}: {e}")
                continue

        df = pd.DataFrame(data)

        # Add metadata
        df['_source_file'] = ifc_path.name
        df['_extract_date'] = datetime.now().isoformat()

        logger.info(f"✅ Extracted {len(df)} elements")
        return df

    def create_analysis_ifc(self, ifc_path: Path, excel_data: pd.DataFrame = None) -> Path:
        """
        Create analysis copy with "_analyse" suffix

        Adds custom property sets for LCA analysis:
        - G55_Prosjektinfo
        - G55_LCA (with Gjenbruksstatus, CO2_kg, etc.)
        """
        analysis_name = ifc_path.stem + "_analyse" + ifc_path.suffix
        analysis_path = self.output_folder / analysis_name

        logger.info(f"🏗️  Creating analysis IFC: {analysis_name}")

        # Open original IFC
        ifc = ifcopenshell.open(str(ifc_path))
        products = ifc.by_type("IfcProduct")

        # File metadata
        file_mod_time = datetime.fromtimestamp(ifc_path.stat().st_mtime).isoformat()
        basert_pa_ifc = f"{ifc_path.name} @ {file_mod_time}"

        for product in products:
            try:
                psets = ifcopenshell.util.element.get_psets(product)

                # Add G55_Prosjektinfo if missing
                if "G55_Prosjektinfo" not in psets:
                    pset = ifcopenshell.api.run("pset.add_pset", ifc, product=product, name="G55_Prosjektinfo")
                    props = {
                        "Prosjekt": "Grønland 55",
                        "Opprettet": datetime.now().isoformat(),
                        "Status": "Analyse"
                    }
                    ifcopenshell.api.run("pset.edit_pset", ifc, pset=pset, properties=props)

                # Add G55_LCA if missing
                if "G55_LCA" not in psets:
                    pset = ifcopenshell.api.run("pset.add_pset", ifc, product=product, name="G55_LCA")
                    props = {
                        "External_ID": product.GlobalId,
                        "Basert_på_IFC": basert_pa_ifc,
                        "Gjenbruksstatus": "NY",  # Default to new
                        "LCA_Status": "Pending",
                        "CO2_kg": "",
                        "LCA_Method": "",
                        "Notes": ""
                    }
                    ifcopenshell.api.run("pset.edit_pset", ifc, pset=pset, properties=props)

            except Exception as e:
                logger.warning(f"Error adding psets to {product.GlobalId}: {e}")
                continue

        # Save analysis IFC
        ifc.write(str(analysis_path))
        logger.info(f"✅ Saved: {analysis_path}")

        return analysis_path

    def sync_excel_to_ifc(self, excel_path: Path, analysis_ifc_path: Path) -> bool:
        """
        Sync Excel edits back to analysis IFC

        Updates property sets in analysis IFC based on Excel columns
        Columns with "." are treated as "PropertySet.PropertyName"
        """
        logger.info(f"🔄 Syncing Excel → IFC")
        logger.info(f"  Excel: {excel_path.name}")
        logger.info(f"  IFC: {analysis_ifc_path.name}")

        try:
            # Read Excel
            df = pd.read_excel(excel_path)

            # Open analysis IFC
            ifc = ifcopenshell.open(str(analysis_ifc_path))

            updated_count = 0

            # Process each row
            for idx, row in df.iterrows():
                try:
                    guid = row['GUID']
                    element = ifc.by_guid(guid)

                    # Update properties
                    for col in row.index:
                        if '.' in col and pd.notna(row[col]) and not col.startswith('_'):
                            # Parse property set and property name
                            pset_name, prop_name = col.rsplit('.', 1)

                            # Get existing psets
                            psets = ifcopenshell.util.element.get_psets(element)

                            if pset_name in psets:
                                # Update existing pset
                                pset_rels = [p for p in element.IsDefinedBy
                                           if p.is_a("IfcRelDefinesByProperties")
                                           and p.RelatingPropertyDefinition.Name == pset_name]

                                if pset_rels:
                                    pset = pset_rels[0].RelatingPropertyDefinition
                                    props = {prop_name: str(row[col])}
                                    ifcopenshell.api.run("pset.edit_pset", ifc, pset=pset, properties=props)
                            else:
                                # Create new pset
                                pset = ifcopenshell.api.run("pset.add_pset", ifc, product=element, name=pset_name)
                                props = {prop_name: str(row[col])}
                                ifcopenshell.api.run("pset.edit_pset", ifc, pset=pset, properties=props)

                    updated_count += 1

                except Exception as e:
                    logger.warning(f"Error updating element {guid}: {e}")
                    continue

            # Save updated IFC
            ifc.write(str(analysis_ifc_path))

            logger.info(f"✅ Updated {updated_count} elements in IFC")
            return True

        except Exception as e:
            logger.error(f"❌ Sync failed: {e}")
            return False

    def run_workflow(self, ifc_filename: str) -> dict:
        """
        Run complete workflow for a single IFC file

        Returns dict with paths to created files
        """
        logger.info("="*60)
        logger.info("🚀 Starting Simple IFC-Excel Sync Workflow")
        logger.info("="*60)

        ifc_path = self.input_folder / ifc_filename

        if not ifc_path.exists():
            logger.error(f"❌ IFC file not found: {ifc_path}")
            return None

        # Step 1: Extract to Excel
        logger.info("\n📊 Step 1: Extracting IFC to Excel")
        df = self.extract_ifc_to_excel(ifc_path)

        excel_name = ifc_path.stem + ".xlsx"
        excel_path = self.output_folder / excel_name

        # Save with formatted columns
        with pd.ExcelWriter(excel_path, engine='openpyxl') as writer:
            df.to_excel(writer, sheet_name='Elements', index=False)
            worksheet = writer.sheets['Elements']
            for col in worksheet.columns:
                worksheet.column_dimensions[col[0].column_letter].width = 25

        logger.info(f"✅ Saved Excel: {excel_path}")

        # Step 2: Create analysis IFC
        logger.info("\n🏗️  Step 2: Creating analysis IFC")
        analysis_path = self.create_analysis_ifc(ifc_path, df)

        logger.info("\n" + "="*60)
        logger.info("✅ Workflow Complete!")
        logger.info("="*60)
        logger.info(f"\n📁 Output files:")
        logger.info(f"  Excel: {excel_path}")
        logger.info(f"  Analysis IFC: {analysis_path}")
        logger.info(f"\n💡 Next steps:")
        logger.info(f"  1. Open {excel_path} in Excel")
        logger.info(f"  2. Edit LCA properties (Gjenbruksstatus, CO2_kg, etc.)")
        logger.info(f"  3. Run sync: sync.sync_excel_to_ifc(excel_path, analysis_path)")
        logger.info(f"  4. Open {analysis_path} in Solibri")

        return {
            'excel': excel_path,
            'analysis_ifc': analysis_path,
            'dataframe': df
        }


def main():
    """Example usage"""
    import sys

    # Initialize sync
    sync = SimpleIFCSync(input_folder="input", output_folder="output")

    # Get IFC file from command line or use default
    if len(sys.argv) > 1:
        ifc_file = sys.argv[1]
    else:
        # List available IFC files
        ifc_files = list(sync.input_folder.glob("*.ifc"))
        if not ifc_files:
            print("❌ No IFC files found in input/ folder")
            print("💡 Place your IFC file in the input/ folder")
            return

        ifc_file = ifc_files[0].name
        print(f"Using first IFC file found: {ifc_file}")

    # Run workflow
    result = sync.run_workflow(ifc_file)

    if result:
        print("\n" + "="*60)
        print("🎉 SUCCESS!")
        print("="*60)


if __name__ == "__main__":
    main()
