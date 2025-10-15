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

    def __init__(self, input_folder: str = "input", output_folder: str = "output", use_temp: bool = False):
        """
        Initialize with input/output folders

        Args:
            input_folder: Folder for input IFC files
            output_folder: Folder for output files (Excel, analysis IFC)
            use_temp: If True, use temporary directory (for Streamlit Cloud)
        """
        if use_temp:
            import tempfile
            # Use temp directory for cloud deployment
            self.temp_dir = Path(tempfile.mkdtemp(prefix="lca_demo_"))
            self.input_folder = self.temp_dir / "input"
            self.output_folder = self.temp_dir / "output"
            self.is_temp = True
        else:
            # Use specified folders for local deployment
            self.input_folder = Path(input_folder)
            self.output_folder = Path(output_folder)
            self.is_temp = False

        # Create folders if they don't exist
        self.input_folder.mkdir(exist_ok=True, parents=True)
        self.output_folder.mkdir(exist_ok=True, parents=True)

        logger.info(f"Input folder: {self.input_folder}")
        logger.info(f"Output folder: {self.output_folder}")
        if use_temp:
            logger.info(f"Using temporary directory (cloud mode)")

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

    def extract_ifc_to_excel(self, ifc_path: Path, progress_callback=None) -> pd.DataFrame:
        """
        Extract IFC elements to Excel DataFrame

        Returns DataFrame with:
        - GUID (External ID for Solibri)
        - BIM_ID (Element ID from authoring tool)
        - Entity type
        - Name, Type, Material
        - All properties from custom property sets

        Args:
            ifc_path: Path to IFC file
            progress_callback: Optional callback function(current, total, message)
        """
        logger.info(f"📖 Extracting IFC: {ifc_path.name}")

        if progress_callback:
            progress_callback(0, 100, "Åpner IFC-fil...")

        ifc = ifcopenshell.open(str(ifc_path))
        products = ifc.by_type("IfcProduct")
        total_products = len(products)

        logger.info(f"Found {total_products} products")

        if progress_callback:
            progress_callback(5, 100, f"Fant {total_products} elementer...")

        # Spatial container elements that don't have ContainedInStructure relationship
        spatial_elements = ('IfcSite', 'IfcBuilding', 'IfcBuildingStorey', 'IfcSpace', 'IfcZone')

        data = []
        for idx, product in enumerate(products):
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

                # Extract Floor/Storey information (skip for spatial container elements)
                row['Floor'] = None
                if not product.is_a() in spatial_elements:
                    if hasattr(product, 'ContainedInStructure'):
                        for rel in product.ContainedInStructure:
                            if rel.is_a('IfcRelContainedInSpatialStructure'):
                                relating_structure = rel.RelatingStructure
                                if relating_structure.is_a('IfcBuildingStorey'):
                                    row['Floor'] = relating_structure.Name if hasattr(relating_structure, 'Name') else relating_structure.LongName
                                    break

                # Extract Zone/Space information
                row['Zone'] = None
                if hasattr(product, 'HasAssignments'):
                    for rel in product.HasAssignments:
                        if rel.is_a('IfcRelAssignsToGroup'):
                            relating_group = rel.RelatingGroup
                            if relating_group.is_a('IfcZone'):
                                row['Zone'] = relating_group.Name if hasattr(relating_group, 'Name') else None
                                break

                # Also check if element is in a space (skip for spatial container elements)
                if not row['Zone'] and not product.is_a() in spatial_elements:
                    if hasattr(product, 'ContainedInStructure'):
                        for rel in product.ContainedInStructure:
                            if rel.is_a('IfcRelContainedInSpatialStructure'):
                                relating_structure = rel.RelatingStructure
                                if relating_structure.is_a('IfcSpace'):
                                    row['Zone'] = relating_structure.Name if hasattr(relating_structure, 'Name') else relating_structure.LongName
                                    break

                # Extract all property sets
                psets = ifcopenshell.util.element.get_psets(product)
                for pset_name, props in psets.items():
                    for prop_name, value in props.items():
                        col_name = f"{pset_name}.{prop_name}"
                        row[col_name] = value if value is not None else ""

                data.append(row)

                # Report progress every 10% or every 100 items
                if progress_callback and (idx % max(1, total_products // 10) == 0 or idx % 100 == 0):
                    progress = int(5 + (idx / total_products * 80))
                    progress_callback(progress, 100, f"Ekstraherer elementer... ({idx}/{total_products})")

            except Exception as e:
                logger.warning(f"Error processing {product.GlobalId}: {e}")
                continue

        if progress_callback:
            progress_callback(85, 100, "Oppretter DataFrame...")

        df = pd.DataFrame(data)

        # Add metadata
        df['_source_file'] = ifc_path.name
        df['_extract_date'] = datetime.now().isoformat()

        logger.info(f"✅ Extracted {len(df)} elements")

        if progress_callback:
            progress_callback(90, 100, f"Ferdig! Ekstrahert {len(df)} elementer")

        return df

    def create_analysis_ifc(self, ifc_path: Path, excel_data: pd.DataFrame = None, progress_callback=None, custom_filename: str = None) -> Path:
        """
        Create analysis copy in "Skiplum demo" folder within original IFC directory

        Adds custom property sets for LCA analysis:
        - G55_Prosjektinfo
        - G55_LCA (with Gjenbruksstatus, CO2_kg, etc.)

        Args:
            ifc_path: Path to IFC file
            excel_data: Optional DataFrame with extracted data
            progress_callback: Optional callback function(current, total, message)
            custom_filename: Optional custom filename for analysis IFC
        """
        # Create "Skiplum demo" folder in the same directory as the original IFC
        skiplum_folder = ifc_path.parent / "Skiplum demo"
        skiplum_folder.mkdir(exist_ok=True, parents=True)

        if custom_filename:
            analysis_name = custom_filename
        else:
            analysis_name = ifc_path.stem + "_analyse" + ifc_path.suffix

        analysis_path = skiplum_folder / analysis_name

        logger.info(f"🏗️  Creating analysis IFC: {analysis_name}")

        if progress_callback:
            progress_callback(0, 100, "Åpner IFC for analyse...")

        # Open original IFC
        ifc = ifcopenshell.open(str(ifc_path))
        products = ifc.by_type("IfcProduct")
        total_products = len(products)

        # File metadata
        file_mod_time = datetime.fromtimestamp(ifc_path.stat().st_mtime).isoformat()
        basert_pa_ifc = f"{ifc_path.name} @ {file_mod_time}"

        if progress_callback:
            progress_callback(5, 100, f"Legger til egenskaper til {total_products} elementer...")

        for idx, product in enumerate(products):
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

                    # Get original MMI value if it exists
                    original_mmi = ""
                    for pset_name, pset_props in psets.items():
                        for prop_name, value in pset_props.items():
                            if 'MMI' in prop_name.upper():
                                original_mmi = str(value) if value else ""
                                break
                        if original_mmi:
                            break

                    props = {
                        "External_ID": product.GlobalId,
                        "Basert_på_IFC": basert_pa_ifc,
                        "Original_MMI": original_mmi,  # Store original MMI value
                        "Gjenbruksstatus": "NY",  # Default to new - editable in demo
                        "LCA_Status": "Pending",
                        "CO2_kg": "",
                        "LCA_Method": "",
                        "Notes": ""
                    }
                    ifcopenshell.api.run("pset.edit_pset", ifc, pset=pset, properties=props)

                # Report progress
                if progress_callback and (idx % max(1, total_products // 10) == 0 or idx % 100 == 0):
                    progress = int(5 + (idx / total_products * 85))
                    progress_callback(progress, 100, f"Behandler element {idx}/{total_products}...")

            except Exception as e:
                logger.warning(f"Error adding psets to {product.GlobalId}: {e}")
                continue

        if progress_callback:
            progress_callback(90, 100, "Lagrer analyse-IFC...")

        # Save analysis IFC
        ifc.write(str(analysis_path))
        logger.info(f"✅ Saved: {analysis_path}")

        if progress_callback:
            progress_callback(100, 100, "Analyse-IFC opprettet!")

        return analysis_path

    def update_ifc_from_dataframe(self, df: pd.DataFrame, analysis_ifc_path: Path) -> bool:
        """
        Update analysis IFC directly from DataFrame (fast, no Excel intermediary)

        This is optimized for demo scenarios where we want instant Solibri updates.
        Updates G55_LCA.Gjenbruksstatus and other editable properties.

        Args:
            df: DataFrame with updated values
            analysis_ifc_path: Path to analysis IFC to update

        Returns:
            True if successful, False otherwise
        """
        logger.info(f"🔄 Updating IFC directly from DataFrame")

        try:
            # Open analysis IFC
            ifc = ifcopenshell.open(str(analysis_ifc_path))

            updated_count = 0

            # Process each row in DataFrame
            for idx, row in df.iterrows():
                try:
                    guid = row['GUID']
                    element = ifc.by_guid(guid)

                    # Update G55_LCA properties
                    psets = ifcopenshell.util.element.get_psets(element)

                    if 'G55_LCA' in psets:
                        # Get existing pset
                        pset_rels = [p for p in element.IsDefinedBy
                                   if p.is_a("IfcRelDefinesByProperties")
                                   and p.RelatingPropertyDefinition.Name == "G55_LCA"]

                        if pset_rels:
                            pset = pset_rels[0].RelatingPropertyDefinition

                            # Update Gjenbruksstatus if changed
                            if 'G55_LCA.Gjenbruksstatus' in row.index and pd.notna(row['G55_LCA.Gjenbruksstatus']):
                                props = {'Gjenbruksstatus': str(row['G55_LCA.Gjenbruksstatus'])}
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
            logger.error(f"❌ IFC update failed: {e}")
            return False

    def save_dataframe_to_excel(self, df: pd.DataFrame, excel_path: Path) -> bool:
        """
        Save DataFrame to Excel file (on-demand)

        Args:
            df: DataFrame with element data
            excel_path: Path where Excel should be saved

        Returns:
            True if successful, False otherwise
        """
        logger.info(f"💾 Saving DataFrame to Excel: {excel_path.name}")

        try:
            # Ensure output directory exists
            excel_path.parent.mkdir(exist_ok=True, parents=True)

            # Save with formatted columns
            with pd.ExcelWriter(excel_path, engine='openpyxl') as writer:
                df.to_excel(writer, sheet_name='Elements', index=False)
                worksheet = writer.sheets['Elements']
                for col in worksheet.columns:
                    worksheet.column_dimensions[col[0].column_letter].width = 25

            logger.info(f"✅ Saved Excel: {excel_path}")
            return True

        except Exception as e:
            logger.error(f"❌ Excel save failed: {e}")
            return False

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

    def run_workflow(self, ifc_filename: str, progress_callback=None, excel_filename: str = None, analysis_ifc_filename: str = None) -> dict:
        """
        Run complete workflow for a single IFC file

        Args:
            ifc_filename: Name of IFC file in input folder
            progress_callback: Optional callback function(step, total_steps, message)
            excel_filename: Optional custom Excel output filename
            analysis_ifc_filename: Optional custom analysis IFC output filename

        Returns dict with paths to created files
        """
        logger.info("="*60)
        logger.info("🚀 Starting Simple IFC-Excel Sync Workflow")
        logger.info("="*60)

        ifc_path = self.input_folder / ifc_filename

        if not ifc_path.exists():
            logger.error(f"❌ IFC file not found: {ifc_path}")
            return None

        # Step 1: Extract IFC to DataFrame
        logger.info("\n📊 Step 1: Extracting IFC to DataFrame")
        if progress_callback:
            progress_callback(1, 3, "Ekstraherer IFC-data...")

        df = self.extract_ifc_to_excel(ifc_path, progress_callback)

        # Note: Excel is NOT saved automatically - only on explicit user request
        logger.info(f"✅ Extracted {len(df)} elements to DataFrame (Excel NOT saved)")

        # Step 2: Create analysis IFC
        logger.info("\n🏗️  Step 2: Creating analysis IFC")
        if progress_callback:
            progress_callback(2, 3, "Oppretter analyse-IFC...")

        analysis_path = self.create_analysis_ifc(ifc_path, df, progress_callback, custom_filename=analysis_ifc_filename)

        if progress_callback:
            progress_callback(3, 3, "Fullført!")

        logger.info("\n" + "="*60)
        logger.info("✅ Workflow Complete!")
        logger.info("="*60)
        logger.info(f"\n📁 Output files:")
        logger.info(f"  Analysis IFC: {analysis_path}")
        logger.info(f"  DataFrame: {len(df)} elements in memory")
        logger.info(f"\n💡 Next steps:")
        logger.info(f"  1. Use Streamlit dashboard to edit Gjenbruksstatus")
        logger.info(f"  2. Changes are saved directly to analysis IFC")
        logger.info(f"  3. Open {analysis_path} in Solibri to see updates")
        logger.info(f"  4. Generate Excel export only if needed (on-demand)")

        return {
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
