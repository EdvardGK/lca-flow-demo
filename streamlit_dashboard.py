#!/usr/bin/env python3
"""
IFC-Excel Sync Dashboard
========================
Streamlit dashboard for viewing and editing IFC data extracted to Excel

Features:
- View/edit Excel data in pivot table format
- LCA analysis page showing volume % by material and MMI codes
- Sync changes back to analysis IFC
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from pathlib import Path
import sys

# Import the sync module
from ifc_sync_simple import SimpleIFCSync

st.set_page_config(
    page_title="BIM LCA Dashboard",
    page_icon="🏗️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for wow factor
st.markdown("""
<style>
    .main-header {
        font-size: 3rem;
        font-weight: bold;
        background: linear-gradient(120deg, #2E7D32, #66BB6A);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 1rem;
    }
    .metric-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 1.5rem;
        border-radius: 10px;
        color: white;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
    }
    .success-box {
        background: linear-gradient(135deg, #2E7D32 0%, #66BB6A 100%);
        padding: 1rem;
        border-radius: 8px;
        color: white;
        text-align: center;
        font-size: 1.2rem;
        margin: 1rem 0;
    }
    .stTabs [data-baseweb="tab-list"] {
        gap: 24px;
    }
    .stTabs [data-baseweb="tab"] {
        height: 50px;
        padding-left: 20px;
        padding-right: 20px;
        font-size: 18px;
    }
</style>
""", unsafe_allow_html=True)

# Initialize session state
if 'sync' not in st.session_state:
    # Use folders relative to script location
    st.session_state.sync = SimpleIFCSync(input_folder="input", output_folder="output")

if 'current_excel' not in st.session_state:
    st.session_state.current_excel = None

if 'current_analysis_ifc' not in st.session_state:
    st.session_state.current_analysis_ifc = None

if 'df' not in st.session_state:
    st.session_state.df = None


def load_excel_data(excel_path: Path):
    """Load Excel data into session state"""
    df = pd.read_excel(excel_path)
    st.session_state.df = df
    st.session_state.current_excel = excel_path
    return df


def extract_volume_from_properties(df: pd.DataFrame) -> pd.DataFrame:
    """Extract volume data from property columns"""
    # Look for volume-related columns
    volume_cols = [col for col in df.columns if 'volume' in col.lower() or 'volum' in col.lower()]

    if volume_cols:
        # Use first volume column found
        df['Volume_m3'] = pd.to_numeric(df[volume_cols[0]], errors='coerce')
    else:
        # If no volume column, estimate from element count
        df['Volume_m3'] = 1.0  # Placeholder

    return df


def extract_mmi_code(df: pd.DataFrame) -> pd.DataFrame:
    """Extract MMI code from property columns"""
    # Look for MMI-related columns
    mmi_cols = [col for col in df.columns if 'MMI' in col.upper()]

    if mmi_cols:
        df['MMI_Code'] = df[mmi_cols[0]]
    else:
        df['MMI_Code'] = 'Unknown'

    return df


def map_mmi_to_status(mmi_code):
    """Map MMI code to readable status"""
    try:
        mmi_num = int(float(str(mmi_code)))
        mapping = {
            300: "NY (Nytt)",
            700: "EKS (Eksisterende)",
            800: "GJEN (Gjenbruk)"
        }
        return mapping.get(mmi_num, f"Annet ({mmi_num})")
    except (ValueError, TypeError):
        if pd.isna(mmi_code) or str(mmi_code).strip() == "":
            return "Ikke angitt"
        return str(mmi_code)


# =============================================================================
# SIDEBAR
# =============================================================================

with st.sidebar:
    st.markdown('<h1 style="color: #2E7D32;">🏗️ BIM LCA</h1>', unsafe_allow_html=True)
    st.markdown("**Klimagassregnskap for byggeprosjekter**")

    st.markdown("---")

    # File upload section
    st.subheader("📁 Load IFC File")

    # List available IFC files
    script_dir = Path(__file__).parent
    ifc_files = list((script_dir / "input").glob("*.ifc"))

    if ifc_files:
        selected_ifc = st.selectbox(
            "Select IFC file",
            options=[f.name for f in ifc_files],
            key="ifc_selector"
        )

        if st.button("🔄 Extract IFC to Excel", type="primary"):
            with st.spinner("Extracting IFC data..."):
                result = st.session_state.sync.run_workflow(selected_ifc)

                if result:
                    st.session_state.current_excel = result['excel']
                    st.session_state.current_analysis_ifc = result['analysis_ifc']
                    st.session_state.df = result['dataframe']
                    st.success(f"✅ Extracted {len(result['dataframe'])} elements")
                    st.rerun()
    else:
        st.info("📂 Place IFC files in the `input/` folder")

    st.markdown("---")

    # Excel file selector
    st.subheader("📊 Load Excel")

    script_dir = Path(__file__).parent
    excel_files = list((script_dir / "output").glob("*.xlsx"))

    if excel_files:
        selected_excel = st.selectbox(
            "Select Excel file",
            options=[f.name for f in excel_files],
            key="excel_selector"
        )

        if st.button("📂 Load Excel"):
            script_dir = Path(__file__).parent
            excel_path = script_dir / "output" / selected_excel
            df = load_excel_data(excel_path)
            st.success(f"✅ Loaded {len(df)} rows")
            st.rerun()

    st.markdown("---")

    # Sync section
    if st.session_state.current_excel and st.session_state.current_analysis_ifc:
        st.subheader("🔄 Sync to IFC")

        st.info(f"**Excel:** {st.session_state.current_excel.name}")
        st.info(f"**Analysis IFC:** {st.session_state.current_analysis_ifc.name}")

        if st.button("💾 Sync Excel → IFC", type="primary"):
            with st.spinner("Syncing changes..."):
                success = st.session_state.sync.sync_excel_to_ifc(
                    st.session_state.current_excel,
                    st.session_state.current_analysis_ifc
                )

                if success:
                    st.success("✅ Sync complete!")
                else:
                    st.error("❌ Sync failed")


# =============================================================================
# MAIN CONTENT
# =============================================================================

# Create tabs
tab1, tab2, tab3 = st.tabs(["📊 Data View", "📈 LCA Analysis", "✏️ Edit Data"])

# =============================================================================
# TAB 1: DATA VIEW
# =============================================================================

with tab1:
    st.header("📊 IFC Data View")

    if st.session_state.df is not None:
        df = st.session_state.df

        # Summary metrics
        col1, col2, col3, col4 = st.columns(4)

        with col1:
            st.metric("Total Elements", len(df))

        with col2:
            unique_types = df['Entity'].nunique() if 'Entity' in df.columns else 0
            st.metric("Element Types", unique_types)

        with col3:
            materials = df['Material'].nunique() if 'Material' in df.columns else 0
            st.metric("Materials", materials)

        with col4:
            if '_source_file' in df.columns:
                st.metric("Source File", df['_source_file'].iloc[0] if len(df) > 0 else "N/A")

        st.markdown("---")

        # Filters
        st.subheader("🔍 Filters")

        col_filter1, col_filter2 = st.columns(2)

        with col_filter1:
            if 'Entity' in df.columns:
                entity_filter = st.multiselect(
                    "Filter by Entity Type",
                    options=sorted(df['Entity'].dropna().unique()),
                    default=[]
                )
                if entity_filter:
                    df = df[df['Entity'].isin(entity_filter)]

        with col_filter2:
            if 'Material' in df.columns:
                material_filter = st.multiselect(
                    "Filter by Material",
                    options=sorted(df['Material'].dropna().unique()),
                    default=[]
                )
                if material_filter:
                    df = df[df['Material'].isin(material_filter)]

        # Data table
        st.subheader("📋 Element Data")

        # Select columns to display
        display_cols = st.multiselect(
            "Select columns to display",
            options=df.columns.tolist(),
            default=['GUID', 'BIM_ID', 'Entity', 'Name', 'Type', 'Material'][:min(6, len(df.columns))]
        )

        if display_cols:
            st.dataframe(df[display_cols], use_container_width=True, height=500)
        else:
            st.dataframe(df, use_container_width=True, height=500)

    else:
        st.info("👈 Load an IFC file or Excel file from the sidebar to get started")


# =============================================================================
# TAB 2: LCA ANALYSIS
# =============================================================================

with tab2:
    st.markdown('<p class="main-header">📈 Klimagassanalyse</p>', unsafe_allow_html=True)
    st.markdown("### Analyse av volum fordelt på material og gjenbruksstatus")

    if st.session_state.df is not None:
        df = st.session_state.df.copy()

        # Extract volume and MMI data
        df = extract_volume_from_properties(df)
        df = extract_mmi_code(df)

        # Map MMI codes to readable status
        df['MMI_Status'] = df['MMI_Code'].apply(map_mmi_to_status)

        # Calculate total volume
        total_volume = df['Volume_m3'].sum()

        # BIG IMPACT SUMMARY with animated metrics
        st.markdown("---")

        # Create impressive gauge charts
        col1, col2, col3 = st.columns(3)

        # Calculate percentages
        ny_volume = df[df['MMI_Status'].str.contains('NY', na=False)]['Volume_m3'].sum()
        ny_pct = (ny_volume / total_volume * 100) if total_volume > 0 else 0

        eks_volume = df[df['MMI_Status'].str.contains('EKS', na=False)]['Volume_m3'].sum()
        eks_pct = (eks_volume / total_volume * 100) if total_volume > 0 else 0

        gjen_volume = df[df['MMI_Status'].str.contains('GJEN', na=False)]['Volume_m3'].sum()
        gjen_pct = (gjen_volume / total_volume * 100) if total_volume > 0 else 0

        with col1:
            # Gauge chart for NY
            fig_ny = go.Figure(go.Indicator(
                mode = "gauge+number+delta",
                value = ny_pct,
                domain = {'x': [0, 1], 'y': [0, 1]},
                title = {'text': "🔴 NYTT", 'font': {'size': 24, 'color': '#FF6B6B'}},
                number = {'suffix': "%", 'font': {'size': 40}},
                gauge = {
                    'axis': {'range': [None, 100], 'tickwidth': 1, 'tickcolor': "darkblue"},
                    'bar': {'color': "#FF6B6B"},
                    'bgcolor': "white",
                    'borderwidth': 2,
                    'bordercolor': "gray",
                    'steps': [
                        {'range': [0, 50], 'color': '#FFE5E5'},
                        {'range': [50, 100], 'color': '#FFCCCC'}],
                    'threshold': {
                        'line': {'color': "red", 'width': 4},
                        'thickness': 0.75,
                        'value': 90}}))
            fig_ny.update_layout(height=300, margin=dict(l=20, r=20, t=50, b=20))
            st.plotly_chart(fig_ny, use_container_width=True)
            st.markdown(f"<div style='text-align:center; font-size:20px;'><b>{ny_volume:,.1f} m³</b></div>", unsafe_allow_html=True)

        with col2:
            # Gauge chart for EKS
            fig_eks = go.Figure(go.Indicator(
                mode = "gauge+number+delta",
                value = eks_pct,
                domain = {'x': [0, 1], 'y': [0, 1]},
                title = {'text': "🟡 EKSISTERENDE", 'font': {'size': 24, 'color': '#FFB84D'}},
                number = {'suffix': "%", 'font': {'size': 40}},
                gauge = {
                    'axis': {'range': [None, 100], 'tickwidth': 1, 'tickcolor': "darkblue"},
                    'bar': {'color': "#FFB84D"},
                    'bgcolor': "white",
                    'borderwidth': 2,
                    'bordercolor': "gray",
                    'steps': [
                        {'range': [0, 50], 'color': '#FFF4E5'},
                        {'range': [50, 100], 'color': '#FFE8CC'}],
                    'threshold': {
                        'line': {'color': "orange", 'width': 4},
                        'thickness': 0.75,
                        'value': 90}}))
            fig_eks.update_layout(height=300, margin=dict(l=20, r=20, t=50, b=20))
            st.plotly_chart(fig_eks, use_container_width=True)
            st.markdown(f"<div style='text-align:center; font-size:20px;'><b>{eks_volume:,.1f} m³</b></div>", unsafe_allow_html=True)

        with col3:
            # Gauge chart for GJEN
            fig_gjen = go.Figure(go.Indicator(
                mode = "gauge+number+delta",
                value = gjen_pct,
                domain = {'x': [0, 1], 'y': [0, 1]},
                title = {'text': "🟢 GJENBRUK", 'font': {'size': 24, 'color': '#66BB6A'}},
                number = {'suffix': "%", 'font': {'size': 40}},
                gauge = {
                    'axis': {'range': [None, 100], 'tickwidth': 1, 'tickcolor': "darkblue"},
                    'bar': {'color': "#66BB6A"},
                    'bgcolor': "white",
                    'borderwidth': 2,
                    'bordercolor': "gray",
                    'steps': [
                        {'range': [0, 50], 'color': '#E8F5E9'},
                        {'range': [50, 100], 'color': '#C8E6C9'}],
                    'threshold': {
                        'line': {'color': "green", 'width': 4},
                        'thickness': 0.75,
                        'value': 10}}))
            fig_gjen.update_layout(height=300, margin=dict(l=20, r=20, t=50, b=20))
            st.plotly_chart(fig_gjen, use_container_width=True)
            st.markdown(f"<div style='text-align:center; font-size:20px;'><b>{gjen_volume:,.1f} m³</b></div>", unsafe_allow_html=True)

        # Impact statement
        if gjen_pct > 20:
            st.markdown(f"""
            <div class="success-box">
                🎉 FANTASTISK! Over {gjen_pct:.0f}% av volumet er gjenbruk - dette er bra for klimaet! 🌍
            </div>
            """, unsafe_allow_html=True)
        elif gjen_pct > 10:
            st.markdown(f"""
            <div style="background: linear-gradient(135deg, #FFB84D 0%, #FFA726 100%); padding: 1rem; border-radius: 8px; color: white; text-align: center; font-size: 1.2rem; margin: 1rem 0;">
                👍 BRA! {gjen_pct:.0f}% gjenbruk - det er rom for forbedring
            </div>
            """, unsafe_allow_html=True)
        else:
            st.markdown(f"""
            <div style="background: linear-gradient(135deg, #FF6B6B 0%, #EE5A52 100%); padding: 1rem; border-radius: 8px; color: white; text-align: center; font-size: 1.2rem; margin: 1rem 0;">
                ⚠️ Kun {gjen_pct:.0f}% gjenbruk - vurder å øke gjenbruksandelen
            </div>
            """, unsafe_allow_html=True)

        st.markdown("---")

        # Group by Material and MMI Status
        if 'Material' in df.columns:
            # Create pivot table
            pivot_data = df.groupby(['Material', 'MMI_Status'])['Volume_m3'].sum().reset_index()
            pivot_data['Percentage'] = (pivot_data['Volume_m3'] / total_volume * 100)

            # Sort by volume
            pivot_data = pivot_data.sort_values('Volume_m3', ascending=False)

            # Charts
            col_chart1, col_chart2 = st.columns(2)

            with col_chart1:
                st.subheader("📊 Volume by MMI Status")

                # Pie chart of MMI status
                mmi_totals = df.groupby('MMI_Status')['Volume_m3'].sum().reset_index()
                mmi_totals = mmi_totals.sort_values('Volume_m3', ascending=False)

                fig_pie = px.pie(
                    mmi_totals,
                    values='Volume_m3',
                    names='MMI_Status',
                    title='Volume Distribution by MMI Code',
                    color='MMI_Status',
                    color_discrete_map={
                        'NY (Nytt)': '#FF6B6B',
                        'EKS (Eksisterende)': '#4ECDC4',
                        'GJEN (Gjenbruk)': '#95E1D3',
                        'Ikke angitt': '#CCCCCC'
                    }
                )
                st.plotly_chart(fig_pie, use_container_width=True)

            with col_chart2:
                st.subheader("📊 Volume by Material")

                # Bar chart of materials
                material_totals = df.groupby('Material')['Volume_m3'].sum().reset_index()
                material_totals = material_totals.sort_values('Volume_m3', ascending=False).head(10)

                fig_bar = px.bar(
                    material_totals,
                    x='Volume_m3',
                    y='Material',
                    orientation='h',
                    title='Top 10 Materials by Volume',
                    labels={'Volume_m3': 'Volume (m³)', 'Material': 'Material'},
                    color='Volume_m3',
                    color_continuous_scale='Viridis'
                )
                st.plotly_chart(fig_bar, use_container_width=True)

            st.markdown("---")

            # Detailed breakdown
            st.subheader("📋 Volume Breakdown by Material and MMI Code")

            # Create stacked bar chart
            fig_stacked = px.bar(
                pivot_data,
                x='Material',
                y='Volume_m3',
                color='MMI_Status',
                title='Volume by Material and MMI Status',
                labels={'Volume_m3': 'Volume (m³)', 'Material': 'Material'},
                color_discrete_map={
                    'NY (Nytt)': '#FF6B6B',
                    'EKS (Eksisterende)': '#4ECDC4',
                    'GJEN (Gjenbruk)': '#95E1D3',
                    'Ikke angitt': '#CCCCCC'
                },
                barmode='stack'
            )
            fig_stacked.update_layout(xaxis_tickangle=-45)
            st.plotly_chart(fig_stacked, use_container_width=True)

            # Data table
            st.subheader("📊 Detailed Data")

            # Pivot table for display
            pivot_display = pivot_data.copy()
            pivot_display['Volume (m³)'] = pivot_display['Volume_m3'].round(2)
            pivot_display['Percentage (%)'] = pivot_display['Percentage'].round(2)

            st.dataframe(
                pivot_display[['Material', 'MMI_Status', 'Volume (m³)', 'Percentage (%)']],
                use_container_width=True,
                height=400
            )

            # Download pivot table
            st.download_button(
                label="📥 Download Pivot Table (CSV)",
                data=pivot_display.to_csv(index=False),
                file_name="lca_analysis_pivot.csv",
                mime="text/csv"
            )

        else:
            st.warning("No Material column found in data")

    else:
        st.info("👈 Load an IFC file or Excel file from the sidebar to get started")


# =============================================================================
# TAB 3: EDIT DATA
# =============================================================================

with tab3:
    st.header("✏️ Edit Element Data")

    if st.session_state.df is not None:
        df = st.session_state.df

        st.info("💡 Edit cells directly in the table below. Changes will be saved when you sync to IFC.")

        # Editable data editor
        edited_df = st.data_editor(
            df,
            use_container_width=True,
            height=600,
            num_rows="dynamic",  # Allow adding/deleting rows
            key="data_editor"
        )

        # Save edited data back to session state
        if st.button("💾 Save Changes to Session", type="primary"):
            st.session_state.df = edited_df
            st.success("✅ Changes saved to session. Use sidebar to sync to IFC.")

        # Export to Excel
        if st.button("📥 Export to Excel"):
            script_dir = Path(__file__).parent
            output_path = script_dir / "output" / "edited_data.xlsx"
            with pd.ExcelWriter(output_path, engine='openpyxl') as writer:
                edited_df.to_excel(writer, sheet_name='Elements', index=False)
            st.success(f"✅ Exported to {output_path}")

    else:
        st.info("👈 Load an IFC file or Excel file from the sidebar to get started")


# =============================================================================
# FOOTER
# =============================================================================

st.markdown("---")
st.caption("🏗️ BIM LCA Sync Dashboard | Built with Streamlit & IfcOpenShell")
