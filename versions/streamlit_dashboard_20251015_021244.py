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
    page_title="BIM LCA-verktøy",
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

# Processing state management
if 'is_processing' not in st.session_state:
    st.session_state.is_processing = False

if 'progress_value' not in st.session_state:
    st.session_state.progress_value = 0

if 'progress_message' not in st.session_state:
    st.session_state.progress_message = ""


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


def extract_gjenbruksstatus(df: pd.DataFrame) -> pd.DataFrame:
    """Extract or create Gjenbruksstatus column for analysis"""
    gjenbruk_col = 'G55_LCA.Gjenbruksstatus'

    # If column already exists, use it
    if gjenbruk_col in df.columns:
        df['Gjenbruksstatus'] = df[gjenbruk_col].fillna('NY')
    else:
        # Try to find MMI codes and map them
        mmi_cols = [col for col in df.columns if 'MMI' in col.upper()]
        if mmi_cols:
            df['Gjenbruksstatus'] = df[mmi_cols[0]].apply(map_mmi_to_status)
        else:
            # Default to NY
            df['Gjenbruksstatus'] = 'NY'

    return df


def map_mmi_to_status(mmi_code):
    """Map MMI code to readable status"""
    try:
        mmi_num = int(float(str(mmi_code)))
        mapping = {
            300: "NY",
            700: "EKS",
            800: "GJEN"
        }
        return mapping.get(mmi_num, "NY")
    except (ValueError, TypeError):
        if pd.isna(mmi_code) or str(mmi_code).strip() == "":
            return "NY"
        # If it's already NY/EKS/GJEN, return as-is
        status_str = str(mmi_code).strip().upper()
        if status_str in ['NY', 'EKS', 'GJEN']:
            return status_str
        return "NY"


def map_status_to_display(status):
    """Map status code to display name"""
    mapping = {
        'NY': 'NY (Nytt)',
        'EKS': 'EKS (Eksisterende)',
        'GJEN': 'GJEN (Gjenbruk)'
    }
    return mapping.get(status, 'Ikke angitt')


# =============================================================================
# SIDEBAR
# =============================================================================

with st.sidebar:
    st.markdown('<h1 style="color: #2E7D32;">🏗️ BIM LCA</h1>', unsafe_allow_html=True)
    st.markdown("**Klimagassregnskap for byggeprosjekter**")

    st.markdown("---")

    # Show processing warning if active
    if st.session_state.is_processing:
        st.warning("⚠️ Behandler fil - vennligst vent...")
        st.markdown("**Ikke lukk vinduet eller klikk på andre knapper**")
        st.markdown("---")

    # File upload section
    st.subheader("📁 Last opp IFC-fil")

    # Option 1: Upload IFC file (for Streamlit Cloud)
    uploaded_file = st.file_uploader(
        "Last opp IFC-fil fra din datamaskin",
        type=['ifc'],
        help="Velg en IFC-fil for analyse",
        disabled=st.session_state.is_processing
    )

    if uploaded_file is not None:
        # Save uploaded file to input folder
        script_dir = Path(__file__).parent
        input_path = script_dir / "input" / uploaded_file.name

        with open(input_path, "wb") as f:
            f.write(uploaded_file.getbuffer())

        st.success(f"📥 Lastet opp: {uploaded_file.name}")

        # Prompt for output filenames
        st.markdown("---")
        st.subheader("📋 Velg filnavn for output")

        # Default names based on uploaded file
        default_basename = Path(uploaded_file.name).stem

        with st.expander("⚙️ Konfigurer filnavn", expanded=True):
            excel_filename = st.text_input(
                "Excel-filnavn",
                value=f"{default_basename}.xlsx",
                help="Filnavn for Excel-output",
                disabled=st.session_state.is_processing,
                key="excel_filename_input"
            )

            analysis_ifc_filename = st.text_input(
                "Analyse-IFC filnavn",
                value=f"{default_basename}_analyse.ifc",
                help="Filnavn for analyse-IFC",
                disabled=st.session_state.is_processing,
                key="analysis_ifc_filename_input"
            )

            st.info(f"📁 Filer vil bli lagret i: `output/`")

        if st.button("🔄 Ekstraher opplastet IFC", type="primary", key="extract_uploaded",
                     disabled=st.session_state.is_processing):
            st.session_state.is_processing = True

            # Create progress containers
            progress_bar = st.progress(0)
            status_text = st.empty()

            def update_progress(current, total, message):
                """Progress callback for extraction"""
                progress_bar.progress(current / total if total > 0 else 0)
                status_text.text(message)

            try:
                result = st.session_state.sync.run_workflow(
                    uploaded_file.name,
                    progress_callback=update_progress,
                    excel_filename=excel_filename,
                    analysis_ifc_filename=analysis_ifc_filename
                )

                if result:
                    st.session_state.current_excel = result['excel']
                    st.session_state.current_analysis_ifc = result['analysis_ifc']
                    st.session_state.df = result['dataframe']
                    st.success(f"✅ Ekstrahert {len(result['dataframe'])} elementer")
                    st.session_state.is_processing = False
                    st.rerun()
            except Exception as e:
                st.error(f"❌ Feil under ekstraksjon: {e}")
                st.session_state.is_processing = False
                st.rerun()

    st.markdown("**ELLER**")

    # Option 2: List available IFC files (for local development)
    script_dir = Path(__file__).parent
    ifc_files = list((script_dir / "input").glob("*.ifc"))

    if ifc_files:
        selected_ifc = st.selectbox(
            "Velg eksisterende IFC-fil",
            options=[f.name for f in ifc_files],
            key="ifc_selector",
            disabled=st.session_state.is_processing
        )

        # Prompt for output filenames
        st.markdown("---")
        st.subheader("📋 Velg filnavn for output")

        # Default names based on selected file
        default_basename = Path(selected_ifc).stem

        with st.expander("⚙️ Konfigurer filnavn", expanded=False):
            excel_filename_selected = st.text_input(
                "Excel-filnavn",
                value=f"{default_basename}.xlsx",
                help="Filnavn for Excel-output",
                disabled=st.session_state.is_processing,
                key="excel_filename_selected"
            )

            analysis_ifc_filename_selected = st.text_input(
                "Analyse-IFC filnavn",
                value=f"{default_basename}_analyse.ifc",
                help="Filnavn for analyse-IFC",
                disabled=st.session_state.is_processing,
                key="analysis_ifc_filename_selected"
            )

            st.info(f"📁 Filer vil bli lagret i: `output/`")

        if st.button("🔄 Ekstraher valgt IFC", type="primary", key="extract_selected",
                     disabled=st.session_state.is_processing):
            st.session_state.is_processing = True

            # Create progress containers
            progress_bar = st.progress(0)
            status_text = st.empty()

            def update_progress(current, total, message):
                """Progress callback for extraction"""
                progress_bar.progress(current / total if total > 0 else 0)
                status_text.text(message)

            try:
                result = st.session_state.sync.run_workflow(
                    selected_ifc,
                    progress_callback=update_progress,
                    excel_filename=excel_filename_selected,
                    analysis_ifc_filename=analysis_ifc_filename_selected
                )

                if result:
                    st.session_state.current_excel = result['excel']
                    st.session_state.current_analysis_ifc = result['analysis_ifc']
                    st.session_state.df = result['dataframe']
                    st.success(f"✅ Ekstrahert {len(result['dataframe'])} elementer")
                    st.session_state.is_processing = False
                    st.rerun()
            except Exception as e:
                st.error(f"❌ Feil under ekstraksjon: {e}")
                st.session_state.is_processing = False
                st.rerun()
    else:
        st.info("📂 Ingen IFC-filer funnet i input-mappen")

    st.markdown("---")

    # Excel file selector
    st.subheader("📊 Last inn Excel")

    script_dir = Path(__file__).parent
    excel_files = list((script_dir / "output").glob("*.xlsx"))

    if excel_files:
        selected_excel = st.selectbox(
            "Velg Excel-fil",
            options=[f.name for f in excel_files],
            key="excel_selector",
            disabled=st.session_state.is_processing
        )

        if st.button("📂 Last inn Excel", disabled=st.session_state.is_processing):
            script_dir = Path(__file__).parent
            excel_path = script_dir / "output" / selected_excel
            df = load_excel_data(excel_path)
            st.success(f"✅ Lastet inn {len(df)} rader")
            st.rerun()

    st.markdown("---")

    # Sync section
    if st.session_state.current_excel and st.session_state.current_analysis_ifc:
        st.subheader("🔄 Synkroniser til IFC")

        st.info(f"**Excel:** {st.session_state.current_excel.name}")
        st.info(f"**Analyse-IFC:** {st.session_state.current_analysis_ifc.name}")

        if st.button("💾 Synkroniser Excel → IFC", type="primary",
                     disabled=st.session_state.is_processing):
            st.session_state.is_processing = True

            progress_bar = st.progress(0)
            status_text = st.empty()

            try:
                status_text.text("Synkroniserer endringer til IFC...")
                progress_bar.progress(0.3)

                success = st.session_state.sync.sync_excel_to_ifc(
                    st.session_state.current_excel,
                    st.session_state.current_analysis_ifc
                )

                progress_bar.progress(1.0)

                if success:
                    st.success("✅ Synkronisering fullført!")
                else:
                    st.error("❌ Synkronisering feilet")

                st.session_state.is_processing = False
                st.rerun()
            except Exception as e:
                st.error(f"❌ Feil under synkronisering: {e}")
                st.session_state.is_processing = False
                st.rerun()

        st.markdown("---")
        st.subheader("📥 Last ned filer")

        # Download Excel
        if st.session_state.current_excel.exists():
            with open(st.session_state.current_excel, "rb") as f:
                st.download_button(
                    label="📊 Last ned Excel",
                    data=f,
                    file_name=st.session_state.current_excel.name,
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    disabled=st.session_state.is_processing
                )

        # Download Analysis IFC
        if st.session_state.current_analysis_ifc.exists():
            with open(st.session_state.current_analysis_ifc, "rb") as f:
                st.download_button(
                    label="🏗️ Last ned Analyse-IFC",
                    data=f,
                    file_name=st.session_state.current_analysis_ifc.name,
                    mime="application/octet-stream",
                    disabled=st.session_state.is_processing
                )


# =============================================================================
# MAIN CONTENT
# =============================================================================

# Create tabs
tab1, tab2, tab3 = st.tabs(["📊 Datavisning", "📈 LCA-analyse", "✏️ Rediger data"])

# =============================================================================
# TAB 1: DATA VIEW
# =============================================================================

with tab1:
    st.header("📊 IFC-datavisning")

    if st.session_state.df is not None:
        df = st.session_state.df

        # Summary metrics
        col1, col2, col3, col4 = st.columns(4)

        with col1:
            st.metric("Totalt antall elementer", len(df))

        with col2:
            unique_types = df['Entity'].nunique() if 'Entity' in df.columns else 0
            st.metric("Elementtyper", unique_types)

        with col3:
            materials = df['Material'].nunique() if 'Material' in df.columns else 0
            st.metric("Materialer", materials)

        with col4:
            if '_source_file' in df.columns:
                st.metric("Kildefil", df['_source_file'].iloc[0] if len(df) > 0 else "N/A")

        st.markdown("---")

        # Filters
        st.subheader("🔍 Filtre")

        col_filter1, col_filter2 = st.columns(2)

        with col_filter1:
            if 'Entity' in df.columns:
                entity_filter = st.multiselect(
                    "Filtrer etter elementtype",
                    options=sorted(df['Entity'].dropna().unique()),
                    default=[]
                )
                if entity_filter:
                    df = df[df['Entity'].isin(entity_filter)]

        with col_filter2:
            if 'Material' in df.columns:
                material_filter = st.multiselect(
                    "Filtrer etter materiale",
                    options=sorted(df['Material'].dropna().unique()),
                    default=[]
                )
                if material_filter:
                    df = df[df['Material'].isin(material_filter)]

        # Data table
        st.subheader("📋 Elementdata")

        # Select columns to display
        display_cols = st.multiselect(
            "Velg kolonner å vise",
            options=df.columns.tolist(),
            default=['GUID', 'BIM_ID', 'Entity', 'Name', 'Type', 'Material'][:min(6, len(df.columns))]
        )

        if display_cols:
            st.dataframe(df[display_cols], use_container_width=True, height=500)
        else:
            st.dataframe(df, use_container_width=True, height=500)

    else:
        st.info("👈 Last inn en IFC-fil eller Excel-fil fra sidepanelet for å komme i gang")


# =============================================================================
# TAB 2: LCA ANALYSIS
# =============================================================================

with tab2:
    st.markdown('<p class="main-header">📈 Klimagassanalyse</p>', unsafe_allow_html=True)
    st.markdown("### Analyse av volum fordelt på material og gjenbruksstatus")

    if st.session_state.df is not None:
        df = st.session_state.df.copy()

        # Extract volume and Gjenbruksstatus
        df = extract_volume_from_properties(df)
        df = extract_gjenbruksstatus(df)

        # Map status to display names
        df['Status_Display'] = df['Gjenbruksstatus'].apply(map_status_to_display)

        # Calculate total volume
        total_volume = df['Volume_m3'].sum()

        # BIG IMPACT SUMMARY with animated metrics
        st.markdown("---")

        # Create impressive gauge charts
        col1, col2, col3 = st.columns(3)

        # Calculate percentages
        ny_volume = df[df['Gjenbruksstatus'] == 'NY']['Volume_m3'].sum()
        ny_pct = (ny_volume / total_volume * 100) if total_volume > 0 else 0

        eks_volume = df[df['Gjenbruksstatus'] == 'EKS']['Volume_m3'].sum()
        eks_pct = (eks_volume / total_volume * 100) if total_volume > 0 else 0

        gjen_volume = df[df['Gjenbruksstatus'] == 'GJEN']['Volume_m3'].sum()
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

        # Group by Material, Type, and Gjenbruksstatus
        if 'Material' in df.columns and 'Entity' in df.columns:
            # Charts - 3 columns
            col_chart1, col_chart2, col_chart3 = st.columns(3)

            with col_chart1:
                st.subheader("📊 Volum etter gjenbruksstatus")

                # Pie chart of status
                status_totals = df.groupby('Status_Display')['Volume_m3'].sum().reset_index()
                status_totals = status_totals.sort_values('Volume_m3', ascending=False)

                fig_pie = px.pie(
                    status_totals,
                    values='Volume_m3',
                    names='Status_Display',
                    title='Volumfordeling etter gjenbruksstatus',
                    color='Status_Display',
                    color_discrete_map={
                        'NY (Nytt)': '#FF6B6B',
                        'EKS (Eksisterende)': '#4ECDC4',
                        'GJEN (Gjenbruk)': '#95E1D3',
                        'Ikke angitt': '#CCCCCC'
                    }
                )
                st.plotly_chart(fig_pie, use_container_width=True)

            with col_chart2:
                st.subheader("📊 Volum etter Type")

                # Bar chart of element types
                type_totals = df.groupby('Entity')['Volume_m3'].sum().reset_index()
                type_totals = type_totals.sort_values('Volume_m3', ascending=False).head(10)

                fig_type = px.bar(
                    type_totals,
                    x='Volume_m3',
                    y='Entity',
                    orientation='h',
                    title='Topp 10 elementtyper etter volum',
                    labels={'Volume_m3': 'Volum (m³)', 'Entity': 'Type'},
                    color='Volume_m3',
                    color_continuous_scale='Blues'
                )
                st.plotly_chart(fig_type, use_container_width=True)

            with col_chart3:
                st.subheader("📊 Volum etter materiale")

                # Bar chart of materials
                material_totals = df.groupby('Material')['Volume_m3'].sum().reset_index()
                material_totals = material_totals.sort_values('Volume_m3', ascending=False).head(10)

                fig_bar = px.bar(
                    material_totals,
                    x='Volume_m3',
                    y='Material',
                    orientation='h',
                    title='Topp 10 materialer etter volum',
                    labels={'Volume_m3': 'Volum (m³)', 'Material': 'Materiale'},
                    color='Volume_m3',
                    color_continuous_scale='Viridis'
                )
                st.plotly_chart(fig_bar, use_container_width=True)

            st.markdown("---")

            # Detailed breakdowns - Type and Material
            st.subheader("📋 Detaljerte volumfordelinger")

            # Create tabs for different breakdown views
            breakdown_tab1, breakdown_tab2, breakdown_tab3 = st.tabs([
                "Type × Status",
                "Materiale × Status",
                "Type × Materiale × Status"
            ])

            with breakdown_tab1:
                st.subheader("Volum etter elementtype og gjenbruksstatus")

                # Type × Status pivot
                type_pivot = df.groupby(['Entity', 'Status_Display'])['Volume_m3'].sum().reset_index()
                type_pivot['Percentage'] = (type_pivot['Volume_m3'] / total_volume * 100)
                type_pivot = type_pivot.sort_values('Volume_m3', ascending=False)

                # Stacked bar chart
                fig_type_stacked = px.bar(
                    type_pivot,
                    x='Entity',
                    y='Volume_m3',
                    color='Status_Display',
                    title='Volum etter elementtype og gjenbruksstatus',
                    labels={'Volume_m3': 'Volum (m³)', 'Entity': 'Elementtype', 'Status_Display': 'Status'},
                    color_discrete_map={
                        'NY (Nytt)': '#FF6B6B',
                        'EKS (Eksisterende)': '#4ECDC4',
                        'GJEN (Gjenbruk)': '#95E1D3',
                        'Ikke angitt': '#CCCCCC'
                    },
                    barmode='stack'
                )
                fig_type_stacked.update_layout(xaxis_tickangle=-45)
                st.plotly_chart(fig_type_stacked, use_container_width=True)

                # Data table
                type_display = type_pivot.copy()
                type_display['Volum (m³)'] = type_display['Volume_m3'].round(2)
                type_display['Prosent (%)'] = type_display['Percentage'].round(2)

                st.dataframe(
                    type_display[['Entity', 'Status_Display', 'Volum (m³)', 'Prosent (%)']],
                    use_container_width=True,
                    height=400
                )

                # Download button
                st.download_button(
                    label="📥 Last ned Type × Status (CSV)",
                    data=type_display.to_csv(index=False),
                    file_name="lca_type_status.csv",
                    mime="text/csv"
                )

            with breakdown_tab2:
                st.subheader("Volum etter materiale og gjenbruksstatus")

                # Material × Status pivot
                material_pivot = df.groupby(['Material', 'Status_Display'])['Volume_m3'].sum().reset_index()
                material_pivot['Percentage'] = (material_pivot['Volume_m3'] / total_volume * 100)
                material_pivot = material_pivot.sort_values('Volume_m3', ascending=False)

                # Stacked bar chart
                fig_material_stacked = px.bar(
                    material_pivot,
                    x='Material',
                    y='Volume_m3',
                    color='Status_Display',
                    title='Volum etter materiale og gjenbruksstatus',
                    labels={'Volume_m3': 'Volum (m³)', 'Material': 'Materiale', 'Status_Display': 'Status'},
                    color_discrete_map={
                        'NY (Nytt)': '#FF6B6B',
                        'EKS (Eksisterende)': '#4ECDC4',
                        'GJEN (Gjenbruk)': '#95E1D3',
                        'Ikke angitt': '#CCCCCC'
                    },
                    barmode='stack'
                )
                fig_material_stacked.update_layout(xaxis_tickangle=-45)
                st.plotly_chart(fig_material_stacked, use_container_width=True)

                # Data table
                material_display = material_pivot.copy()
                material_display['Volum (m³)'] = material_display['Volume_m3'].round(2)
                material_display['Prosent (%)'] = material_display['Percentage'].round(2)

                st.dataframe(
                    material_display[['Material', 'Status_Display', 'Volum (m³)', 'Prosent (%)']],
                    use_container_width=True,
                    height=400
                )

                # Download button
                st.download_button(
                    label="📥 Last ned Materiale × Status (CSV)",
                    data=material_display.to_csv(index=False),
                    file_name="lca_material_status.csv",
                    mime="text/csv"
                )

            with breakdown_tab3:
                st.subheader("Volum etter type, materiale og gjenbruksstatus")

                # Type × Material × Status pivot
                full_pivot = df.groupby(['Entity', 'Material', 'Status_Display'])['Volume_m3'].sum().reset_index()
                full_pivot['Percentage'] = (full_pivot['Volume_m3'] / total_volume * 100)
                full_pivot = full_pivot.sort_values('Volume_m3', ascending=False)

                # Display as table (too complex for chart)
                full_display = full_pivot.copy()
                full_display['Volum (m³)'] = full_display['Volume_m3'].round(2)
                full_display['Prosent (%)'] = full_display['Percentage'].round(2)

                st.dataframe(
                    full_display[['Entity', 'Material', 'Status_Display', 'Volum (m³)', 'Prosent (%)']],
                    use_container_width=True,
                    height=500
                )

                # Download button
                st.download_button(
                    label="📥 Last ned Type × Materiale × Status (CSV)",
                    data=full_display.to_csv(index=False),
                    file_name="lca_full_pivot.csv",
                    mime="text/csv"
                )

        else:
            st.warning("Ingen materialkolonne funnet i dataene")

    else:
        st.info("👈 Last inn en IFC-fil eller Excel-fil fra sidepanelet for å komme i gang")


# =============================================================================
# TAB 3: EDIT DATA
# =============================================================================

with tab3:
    st.header("✏️ Rediger gjenbruksstatus")

    if st.session_state.df is not None:
        df = st.session_state.df.copy()

        # Ensure G55_LCA.Gjenbruksstatus column exists
        gjenbruk_col = 'G55_LCA.Gjenbruksstatus'
        if gjenbruk_col not in df.columns:
            df[gjenbruk_col] = 'NY'
            st.warning("⚠️ Gjenbruksstatus-kolonne mangler. La til med standardverdier (NY).")

        # Create tabs for different editing modes
        edit_tab1, edit_tab2 = st.tabs(["🎯 Rask redigering", "📋 Avansert redigering"])

        with edit_tab1:
            st.subheader("Endre gjenbruksstatus for flere elementer")
            st.info("💡 Velg elementer og sett gjenbruksstatus i bulk. Perfekt for demo!")

            # Filters for selecting elements
            col_f1, col_f2 = st.columns(2)

            with col_f1:
                entity_options = ['Alle'] + sorted(df['Entity'].dropna().unique().tolist())
                selected_entity = st.selectbox(
                    "Filtrer etter elementtype",
                    options=entity_options,
                    key="entity_filter_edit"
                )

            with col_f2:
                material_options = ['Alle'] + sorted(df['Material'].dropna().unique().tolist())
                selected_material = st.selectbox(
                    "Filtrer etter materiale",
                    options=material_options,
                    key="material_filter_edit"
                )

            # Additional filters - Floor and Zone
            col_f3, col_f4 = st.columns(2)

            with col_f3:
                if 'Floor' in df.columns:
                    floor_options = ['Alle'] + sorted([str(f) for f in df['Floor'].dropna().unique().tolist()])
                    selected_floor = st.selectbox(
                        "Filtrer etter etasje",
                        options=floor_options,
                        key="floor_filter_edit"
                    )
                else:
                    selected_floor = 'Alle'

            with col_f4:
                if 'Zone' in df.columns:
                    zone_options = ['Alle'] + sorted([str(z) for z in df['Zone'].dropna().unique().tolist()])
                    selected_zone = st.selectbox(
                        "Filtrer etter sone/rom",
                        options=zone_options,
                        key="zone_filter_edit"
                    )
                else:
                    selected_zone = 'Alle'

            # Apply filters
            filtered_df = df.copy()
            if selected_entity != 'Alle':
                filtered_df = filtered_df[filtered_df['Entity'] == selected_entity]
            if selected_material != 'Alle':
                filtered_df = filtered_df[filtered_df['Material'] == selected_material]
            if selected_floor != 'Alle' and 'Floor' in df.columns:
                filtered_df = filtered_df[filtered_df['Floor'].astype(str) == selected_floor]
            if selected_zone != 'Alle' and 'Zone' in df.columns:
                filtered_df = filtered_df[filtered_df['Zone'].astype(str) == selected_zone]

            st.markdown(f"**{len(filtered_df)} elementer** matcher filter")

            # Show current distribution
            st.markdown("### Nåværende fordeling:")
            col_dist1, col_dist2, col_dist3 = st.columns(3)

            ny_count = (filtered_df[gjenbruk_col] == 'NY').sum()
            eks_count = (filtered_df[gjenbruk_col] == 'EKS').sum()
            gjen_count = (filtered_df[gjenbruk_col] == 'GJEN').sum()

            with col_dist1:
                st.metric("🔴 NYTT", ny_count)
            with col_dist2:
                st.metric("🟡 EKSISTERENDE", eks_count)
            with col_dist3:
                st.metric("🟢 GJENBRUK", gjen_count)

            st.markdown("---")

            # Bulk edit section
            st.subheader("Velg nye verdier for filtrerte elementer:")

            # Multiple edit options
            col_edit1, col_edit2, col_edit3 = st.columns(3)

            with col_edit1:
                new_status = st.selectbox(
                    "Gjenbruksstatus",
                    options=['(Ikke endre)', 'NY', 'EKS', 'GJEN'],
                    index=0,
                    key="new_status_select",
                    help="Velg hvilken status de filtrerte elementene skal få"
                )

            with col_edit2:
                demo_materials = ['(Ikke endre)', 'Betong', 'Stål', 'Tre', 'Glass', 'Gips', 'Tegl', 'Isolasjon']
                new_demo_material = st.selectbox(
                    "Demo Material",
                    options=demo_materials,
                    index=0,
                    key="new_demo_material_select",
                    help="Sett demo-materiale for LCA-analyse"
                )

            with col_edit3:
                demo_types = ['(Ikke endre)', 'Bærekonstruksjon', 'Fasade', 'Tak', 'Gulv', 'Vegg', 'Fundament']
                new_demo_type = st.selectbox(
                    "Demo Type",
                    options=demo_types,
                    index=0,
                    key="new_demo_type_select",
                    help="Sett demo-type for LCA-analyse"
                )

            if st.button("✅ Oppdater valgte elementer", type="primary"):
                # Update the filtered rows
                mask = df.index.isin(filtered_df.index)

                changes_made = []

                if new_status != '(Ikke endre)':
                    df.loc[mask, gjenbruk_col] = new_status
                    changes_made.append(f"Gjenbruksstatus: {new_status}")

                if new_demo_material != '(Ikke endre)':
                    demo_mat_col = 'G55_LCA.Demo_Material'
                    if demo_mat_col not in df.columns:
                        df[demo_mat_col] = ''
                    df.loc[mask, demo_mat_col] = new_demo_material
                    changes_made.append(f"Demo Material: {new_demo_material}")

                if new_demo_type != '(Ikke endre)':
                    demo_type_col = 'G55_LCA.Demo_Type'
                    if demo_type_col not in df.columns:
                        df[demo_type_col] = ''
                    df.loc[mask, demo_type_col] = new_demo_type
                    changes_made.append(f"Demo Type: {new_demo_type}")

                if changes_made:
                    # Update session state
                    st.session_state.df = df

                    # Update Excel if it exists
                    if st.session_state.current_excel:
                        with pd.ExcelWriter(st.session_state.current_excel, engine='openpyxl') as writer:
                            df.to_excel(writer, sheet_name='Elements', index=False)
                            worksheet = writer.sheets['Elements']
                            for col in worksheet.columns:
                                worksheet.column_dimensions[col[0].column_letter].width = 25

                    change_summary = " | ".join(changes_made)
                    st.success(f"✅ Oppdatert {len(filtered_df)} elementer: {change_summary}")
                    st.rerun()
                else:
                    st.warning("⚠️ Ingen endringer valgt")

            # Preview table with original vs analysis comparison
            st.markdown("### Forhåndsvisning av filtrerte elementer:")

            # Show original MMI vs G55_LCA comparison
            preview_cols = ['Entity', 'Name', 'Material', 'Floor', 'Zone']

            # Add original MMI if it exists
            original_mmi_col = 'G55_LCA.Original_MMI'
            if original_mmi_col in filtered_df.columns:
                preview_cols.append(original_mmi_col)

            # Add G55_LCA columns
            preview_cols.extend([gjenbruk_col, 'G55_LCA.Demo_Material', 'G55_LCA.Demo_Type'])

            available_cols = [col for col in preview_cols if col in filtered_df.columns]

            st.dataframe(
                filtered_df[available_cols],
                use_container_width=True,
                height=300
            )

        with edit_tab2:
            st.subheader("Avansert databehandling")
            st.info("💡 Rediger G55_LCA analyse-egenskaper. Original IFC-data er synlig men kan ikke endres her.")

            # Ensure demo columns exist
            if 'G55_LCA.Demo_Material' not in df.columns:
                df['G55_LCA.Demo_Material'] = ''
            if 'G55_LCA.Demo_Type' not in df.columns:
                df['G55_LCA.Demo_Type'] = ''

            # Editable data editor with proper column configuration
            column_config = {
                gjenbruk_col: st.column_config.SelectboxColumn(
                    "Gjenbruksstatus",
                    help="Velg gjenbruksstatus (NY/EKS/GJEN)",
                    options=["NY", "EKS", "GJEN"],
                    required=True
                ),
                'G55_LCA.Demo_Material': st.column_config.SelectboxColumn(
                    "Demo Material",
                    help="Materiale for demo-analyse",
                    options=['', 'Betong', 'Stål', 'Tre', 'Glass', 'Gips', 'Tegl', 'Isolasjon'],
                    required=False
                ),
                'G55_LCA.Demo_Type': st.column_config.SelectboxColumn(
                    "Demo Type",
                    help="Type for demo-analyse",
                    options=['', 'Bærekonstruksjon', 'Fasade', 'Tak', 'Gulv', 'Vegg', 'Fundament'],
                    required=False
                ),
                'G55_LCA.Original_MMI': st.column_config.TextColumn(
                    "Original MMI",
                    help="Original MMI-verdi fra IFC (kun visning)",
                    disabled=True
                ),
                'Material': st.column_config.TextColumn(
                    "Material (IFC)",
                    help="Original materiale fra IFC (kun visning)",
                    disabled=True
                ),
                'Entity': st.column_config.TextColumn(
                    "Entity (IFC)",
                    help="Original elementtype fra IFC (kun visning)",
                    disabled=True
                ),
                'Floor': st.column_config.TextColumn(
                    "Floor",
                    help="Etasje (kun visning)",
                    disabled=True
                ),
                'Zone': st.column_config.TextColumn(
                    "Zone",
                    help="Sone/Rom (kun visning)",
                    disabled=True
                )
            }

            edited_df = st.data_editor(
                df,
                use_container_width=True,
                height=500,
                num_rows="dynamic",
                key="data_editor",
                column_config=column_config
            )

            # Save changes
            col_save1, col_save2 = st.columns(2)

            with col_save1:
                if st.button("💾 Lagre alle endringer", type="primary"):
                    st.session_state.df = edited_df

                    # Update the current Excel file if it exists
                    if st.session_state.current_excel:
                        with pd.ExcelWriter(st.session_state.current_excel, engine='openpyxl') as writer:
                            edited_df.to_excel(writer, sheet_name='Elements', index=False)
                            worksheet = writer.sheets['Elements']
                            for col in worksheet.columns:
                                worksheet.column_dimensions[col[0].column_letter].width = 25
                        st.success("✅ Endringer lagret! Bruk sidepanelet for å synkronisere til IFC.")
                    else:
                        st.success("✅ Endringer lagret i session. Bruk sidepanelet for å synkronisere til IFC.")

            with col_save2:
                # Download edited data as Excel
                from io import BytesIO
                buffer = BytesIO()
                with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
                    edited_df.to_excel(writer, sheet_name='Elements', index=False)
                buffer.seek(0)

                st.download_button(
                    label="📥 Last ned redigert Excel",
                    data=buffer,
                    file_name="redigerte_data.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )

    else:
        st.info("👈 Last inn en IFC-fil eller Excel-fil fra sidepanelet for å komme i gang")


# =============================================================================
# FOOTER
# =============================================================================

st.markdown("---")
st.caption("🏗️ BIM LCA Synkronisering | Laget med Streamlit & IfcOpenShell")
