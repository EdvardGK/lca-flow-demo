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

# Detect deployment environment
def is_cloud_deployment():
    """Detect if running on Streamlit Cloud"""
    import os
    # Streamlit Cloud sets these environment variables
    return os.getenv('STREAMLIT_SHARING_MODE') is not None or \
           os.getenv('STREAMLIT_SERVER_HEADLESS') == 'true'

# Initialize session state
if 'sync' not in st.session_state:
    # Auto-detect environment
    use_temp = is_cloud_deployment()
    st.session_state.sync = SimpleIFCSync(input_folder="input", output_folder="output", use_temp=use_temp)
    st.session_state.is_cloud = use_temp

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

    # Show deployment mode
    if st.session_state.is_cloud:
        st.info("☁️ **Cloud Mode**: Download analysis IFC to use with Solibri")
    else:
        st.success("💻 **Local Mode**: Solibri can watch analysis IFC for live updates")

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

        # Auto-generate filenames based on uploaded file
        default_basename = Path(uploaded_file.name).stem
        excel_filename = f"{default_basename}.xlsx"
        analysis_ifc_filename = f"{default_basename}_analyse.ifc"

        if st.button("🔄 Analyser modell", type="primary", key="extract_uploaded",
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
                    st.session_state.current_analysis_ifc = result['analysis_ifc']
                    st.session_state.df = result['dataframe']
                    st.success(f"✅ Ekstrahert {len(result['dataframe'])} elementer")
                    st.info(f"📁 Analyse-IFC lagret i: {result['analysis_ifc']}")
                    st.session_state.is_processing = False
                    st.rerun()
            except Exception as e:
                st.error(f"❌ Feil under ekstraksjon: {e}")
                st.session_state.is_processing = False
                st.rerun()

    # Developer mode: Local file selection (hidden by default)
    with st.expander("🔧 Utvikler: Bruk lokal fil", expanded=False):
        script_dir = Path(__file__).parent
        ifc_files = list((script_dir / "input").glob("*.ifc"))

        if ifc_files:
            selected_ifc = st.selectbox(
                "Velg eksisterende IFC-fil",
                options=[f.name for f in ifc_files],
                key="ifc_selector",
                disabled=st.session_state.is_processing
            )

            # Auto-generate filenames based on selected file
            default_basename = Path(selected_ifc).stem
            excel_filename_selected = f"{default_basename}.xlsx"
            analysis_ifc_filename_selected = f"{default_basename}_analyse.ifc"

            if st.button("🔄 Analyser valgt fil", type="primary", key="extract_selected",
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
                        st.session_state.current_analysis_ifc = result['analysis_ifc']
                        st.session_state.df = result['dataframe']
                        st.success(f"✅ Ekstrahert {len(result['dataframe'])} elementer")
                        st.info(f"📁 Analyse-IFC lagret i: {result['analysis_ifc']}")
                        st.session_state.is_processing = False
                        st.rerun()
                except Exception as e:
                    st.error(f"❌ Feil under ekstraksjon: {e}")
                    st.session_state.is_processing = False
                    st.rerun()
        else:
            st.info("📂 Ingen IFC-filer funnet i input-mappen")

    st.markdown("---")

    # Optional download section
    if st.session_state.current_analysis_ifc:
        st.subheader("📥 Eksporter filer")

        st.caption("💡 Analyse-IFC oppdateres automatisk. Excel genereres kun på forespørsel.")

        # Show analysis IFC location
        st.info(f"📁 Analyse-IFC: `{st.session_state.current_analysis_ifc}`")

        # Generate and Save Excel button
        if st.session_state.df is not None:
            col1, col2 = st.columns(2)

            with col1:
                if st.button("💾 Generer og lagre Excel",
                           type="secondary",
                           use_container_width=True,
                           disabled=st.session_state.is_processing,
                           help="Lagrer Excel-fil til output-mappen"):
                    # Generate filename
                    excel_path = st.session_state.sync.output_folder / f"{st.session_state.current_analysis_ifc.stem}.xlsx"

                    # Save Excel
                    success = st.session_state.sync.save_dataframe_to_excel(st.session_state.df, excel_path)

                    if success:
                        st.success(f"✅ Excel lagret: {excel_path}")
                    else:
                        st.error("❌ Kunne ikke lagre Excel")

            with col2:
                # Download current DataFrame as Excel (in-memory, no save)
                from io import BytesIO
                buffer = BytesIO()
                with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
                    st.session_state.df.to_excel(writer, sheet_name='Elements', index=False)
                    worksheet = writer.sheets['Elements']
                    for col in worksheet.columns:
                        worksheet.column_dimensions[col[0].column_letter].width = 25
                buffer.seek(0)

                st.download_button(
                    label="📥 Last ned Excel",
                    data=buffer,
                    file_name=f"{st.session_state.current_analysis_ifc.stem}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    help="Last ned Excel-fil direkte (lagres ikke på disk)",
                    disabled=st.session_state.is_processing,
                    use_container_width=True
                )

        # Download Analysis IFC
        if st.session_state.current_analysis_ifc.exists():
            with open(st.session_state.current_analysis_ifc, "rb") as f:
                st.download_button(
                    label="🏗️ Last ned Analyse-IFC",
                    data=f,
                    file_name=st.session_state.current_analysis_ifc.name,
                    mime="application/octet-stream",
                    help="Last ned oppdatert IFC-fil fra Skiplum demo-mappen",
                    disabled=st.session_state.is_processing,
                    use_container_width=True
                )


# =============================================================================
# MAIN CONTENT
# =============================================================================

# Create tabs - simplified to 2 main tabs
tab1, tab2 = st.tabs(["📈 Klimagassanalyse", "✏️ Forbedre prosjektet"])

# =============================================================================
# TAB 1: LCA ANALYSIS (formerly TAB 2)
# =============================================================================

with tab1:
    st.markdown('<p class="main-header">📈 Klimagassanalyse</p>', unsafe_allow_html=True)

    if st.session_state.df is not None:
        df = st.session_state.df.copy()

        # Quick overview metrics at the top
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
                source_file = df['_source_file'].iloc[0] if len(df) > 0 else "N/A"
                st.metric("Kildefil", Path(source_file).stem if source_file != "N/A" else "N/A")

        st.markdown("---")
        st.markdown("### Analyse av volum fordelt på material og gjenbruksstatus")

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

        # Enhanced impact narrative with clear problem/solution messaging
        st.markdown("---")
        st.markdown("### 📊 Klimaavtrykk-vurdering")

        if gjen_pct > 30:
            st.success(f"""
**✅ FANTASTISK RESULTAT!**

Over **{gjen_pct:.0f}% gjenbruk** - prosjektet har et betydelig redusert klimaavtrykk! Dette er et godt eksempel på sirkulær økonomi i praksis.

**Miljøgevinst**: Dere har redusert CO₂-utslipp, ressursbruk og avfall sammenlignet med 100% nye materialer.
            """)
        elif gjen_pct > 10:
            st.warning(f"""
**👍 BRA START - MEN ROM FOR FORBEDRING**

Prosjektet har **{gjen_pct:.0f}% gjenbruk**, men det er potensiale for mer.

**Anbefaling**: Gå til "Forbedre prosjektet" for å utforske hvilke elementer som kan konverteres til gjenbruk eller eksisterende materialer.
            """)
            st.info("💡 **NESTE STEG**: Prøv å endre betongvegger eller stålkonstruksjoner til gjenbruk - dette gir stor klimagevinst!")
        else:
            st.error(f"""
**❌ PROBLEM: HØY KLIMABELASTNING**

Over **{ny_pct:.0f}% nye materialer** - dette gir høye klimagassutslipp og stor miljøbelastning.

**Hvorfor er dette et problem?**
- Nye materialer krever produksjon med høyt energiforbruk
- Økte CO₂-utslipp sammenlignet med gjenbruk
- Unødvendig ressursbruk når eksisterende/gjenbrukte alternativer finnes
            """)
            st.info(f"""
**💡 LØSNING: Gå til "Forbedre prosjektet"-fanen**

Ved å endre noen elementer til GJEN (gjenbruk) eller EKS (eksisterende) kan dere drastisk redusere klimaavtrykket.

**Forslag til raske gevinster:**
- Endre betongvegger til gjenbruk → stor CO₂-reduksjon
- Behold eksisterende stålkonstruksjoner → kutt produksjonsutslipp
- Gjenbruk av taktekking og fasadepaneler → mindre avfall
            """)

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

            # Detailed breakdowns - converted to expanders
            st.subheader("📋 Detaljerte volumfordelinger")
            st.caption("Klikk for å utvide hver analyse")

            # Breakdown 1: Type × Status
            with st.expander("📊 Volum etter elementtype og gjenbruksstatus", expanded=False):
                st.markdown("#### Volum etter elementtype og gjenbruksstatus")

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

            # Breakdown 2: Materiale × Status
            with st.expander("📊 Volum etter materiale og gjenbruksstatus", expanded=False):
                st.markdown("#### Volum etter materiale og gjenbruksstatus")

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

            # Breakdown 3: Type × Materiale × Status
            with st.expander("📊 Volum etter type, materiale og gjenbruksstatus", expanded=False):
                st.markdown("#### Volum etter type, materiale og gjenbruksstatus")

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
# TAB 2: EDIT DATA (formerly TAB 3)
# =============================================================================

with tab2:
    st.header("✏️ Forbedre prosjektet")
    st.markdown("**Endre gjenbruksstatus for å redusere klimaavtrykket**")

    if st.session_state.df is not None:
        df = st.session_state.df.copy()

        # Ensure G55_LCA.Gjenbruksstatus column exists
        gjenbruk_col = 'G55_LCA.Gjenbruksstatus'
        if gjenbruk_col not in df.columns:
            df[gjenbruk_col] = 'NY'
            st.warning("⚠️ Gjenbruksstatus-kolonne mangler. La til med standardverdier (NY).")

        # Demo scenarios - one-click preset changes
        st.subheader("📖 Demo-scenarier")
        st.caption("Klikk for å vise raske klimaforbedringer (endringer lagres automatisk)")

        col_scenario1, col_scenario2, col_scenario3 = st.columns(3)

        with col_scenario1:
            if st.button("🏗️ Gjenbruk betongvegger", type="secondary", use_container_width=True):
                # Filter: Walls with Concrete
                if 'Entity' in df.columns and 'Material' in df.columns:
                    mask = (df['Entity'].str.contains('Wall', case=False, na=False)) & \
                           (df['Material'].str.contains('Concrete|Betong', case=False, na=False))
                    affected = mask.sum()
                    df.loc[mask, gjenbruk_col] = 'GJEN'
                    st.session_state.df = df

                    # Update analysis IFC directly (fast, Solibri sees changes immediately)
                    if st.session_state.current_analysis_ifc:
                        with st.spinner("Oppdaterer IFC-fil..."):
                            st.session_state.sync.update_ifc_from_dataframe(df, st.session_state.current_analysis_ifc)

                    st.success(f"✅ Endret {affected} betongvegger til GJENBRUK!")
                    if st.session_state.is_cloud:
                        st.info("💡 Gå til 'Klimagassanalyse' for å se effekten | Last ned IFC for å bruke i Solibri")
                    else:
                        st.info("💡 Gå til 'Klimagassanalyse' for å se effekten | Solibri vil vise oppdateringsprompt")
                    st.rerun()

        with col_scenario2:
            if st.button("🌳 Behold eksisterende stål", type="secondary", use_container_width=True):
                # Filter: Elements with Steel/Stål
                if 'Material' in df.columns:
                    mask = df['Material'].str.contains('Steel|Stål', case=False, na=False)
                    affected = mask.sum()
                    df.loc[mask, gjenbruk_col] = 'EKS'
                    st.session_state.df = df

                    # Update analysis IFC directly (fast, Solibri sees changes immediately)
                    if st.session_state.current_analysis_ifc:
                        with st.spinner("Oppdaterer IFC-fil..."):
                            st.session_state.sync.update_ifc_from_dataframe(df, st.session_state.current_analysis_ifc)

                    st.success(f"✅ Endret {affected} stålelementer til EKSISTERENDE!")
                    st.info("💡 Gå til 'Klimagassanalyse' for å se effekten | Solibri vil vise oppdateringsprompt")
                    st.rerun()

        with col_scenario3:
            if st.button("♻️ Gjenbruk alle dekker", type="secondary", use_container_width=True):
                # Filter: Slabs
                if 'Entity' in df.columns:
                    mask = df['Entity'].str.contains('Slab|Dekke', case=False, na=False)
                    affected = mask.sum()
                    df.loc[mask, gjenbruk_col] = 'GJEN'
                    st.session_state.df = df

                    # Update analysis IFC directly (fast, Solibri sees changes immediately)
                    if st.session_state.current_analysis_ifc:
                        with st.spinner("Oppdaterer IFC-fil..."):
                            st.session_state.sync.update_ifc_from_dataframe(df, st.session_state.current_analysis_ifc)

                    st.success(f"✅ Endret {affected} dekker til GJENBRUK!")
                    st.info("💡 Gå til 'Klimagassanalyse' for å se effekten | Solibri vil vise oppdateringsprompt")
                    st.rerun()

        # Reset button
        col_reset1, col_reset2, col_reset3 = st.columns([1, 1, 1])
        with col_reset2:
            if st.button("🔄 Tilbakestill alle til NY", type="secondary", use_container_width=True):
                df[gjenbruk_col] = 'NY'
                st.session_state.df = df

                # Update analysis IFC directly
                if st.session_state.current_analysis_ifc:
                    with st.spinner("Oppdaterer IFC-fil..."):
                        st.session_state.sync.update_ifc_from_dataframe(df, st.session_state.current_analysis_ifc)

                st.warning("⚠️ Tilbakestilt alle elementer til NYE | Solibri vil vise oppdateringsprompt")
                st.rerun()

        st.markdown("---")

        # Main editing interface (formerly "Rask redigering")
        st.subheader("🎯 Manuell redigering")
        st.info("💡 Filtrer elementer og sett gjenbruksstatus manuelt")

        # Primary filter - always visible
        entity_options = ['Alle'] + sorted(df['Entity'].dropna().unique().tolist())
        selected_entity = st.selectbox(
            "📋 Filtrer etter elementtype",
            options=entity_options,
            key="entity_filter_edit",
            help="Velg hvilken type elementer du vil endre"
        )

        # Additional filters - hidden by default (progressive disclosure)
        with st.expander("🔍 Flere filtre (Materiale, Etasje, Sone)", expanded=False):
            col_f1, col_f2 = st.columns(2)

            with col_f1:
                material_options = ['Alle'] + sorted(df['Material'].dropna().unique().tolist())
                selected_material = st.selectbox(
                    "Materiale",
                    options=material_options,
                    key="material_filter_edit"
                )

                if 'Floor' in df.columns:
                    floor_options = ['Alle'] + sorted([str(f) for f in df['Floor'].dropna().unique().tolist()])
                    selected_floor = st.selectbox(
                        "Etasje",
                        options=floor_options,
                        key="floor_filter_edit"
                    )
                else:
                    selected_floor = 'Alle'

            with col_f2:
                if 'Zone' in df.columns:
                    zone_options = ['Alle'] + sorted([str(z) for z in df['Zone'].dropna().unique().tolist()])
                    selected_zone = st.selectbox(
                        "Sone/Rom",
                        options=zone_options,
                        key="zone_filter_edit"
                    )
                else:
                    selected_zone = 'Alle'

        # If expander not used, set defaults
        if 'selected_material' not in locals():
            selected_material = 'Alle'
        if 'selected_floor' not in locals():
            selected_floor = 'Alle'
        if 'selected_zone' not in locals():
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
        st.subheader("Velg ny gjenbruksstatus for filtrerte elementer:")

        # Single edit option - only Gjenbruksstatus matters
        new_status = st.selectbox(
            "Gjenbruksstatus",
            options=['(Ikke endre)', 'NY', 'EKS', 'GJEN'],
            index=0,
            key="new_status_select",
            help="Velg hvilken status de filtrerte elementene skal få"
        )

        if st.button("✅ Oppdater valgte elementer", type="primary"):
            # Update the filtered rows
            mask = df.index.isin(filtered_df.index)

            if new_status != '(Ikke endre)':
                df.loc[mask, gjenbruk_col] = new_status
                # Update session state
                st.session_state.df = df

                # Update analysis IFC directly (fast, Solibri sees changes immediately)
                if st.session_state.current_analysis_ifc:
                    with st.spinner("Oppdaterer IFC-fil..."):
                        st.session_state.sync.update_ifc_from_dataframe(df, st.session_state.current_analysis_ifc)

                st.success(f"✅ Oppdatert {len(filtered_df)} elementer til {new_status} | Solibri vil vise oppdateringsprompt")
                st.rerun()
            else:
                st.warning("⚠️ Velg en gjenbruksstatus")

        # Preview table - simplified to show only what matters
        st.markdown("### Forhåndsvisning av filtrerte elementer:")

        # Show only essential columns
        preview_cols = ['Entity', 'Material', gjenbruk_col]

        # Optionally show original MMI for reference
        original_mmi_col = 'G55_LCA.Original_MMI'
        if original_mmi_col in filtered_df.columns:
            preview_cols.append(original_mmi_col)

        available_cols = [col for col in preview_cols if col in filtered_df.columns]

        st.dataframe(
            filtered_df[available_cols],
            use_container_width=True,
            height=300
        )

        # Optional: Show more details in expander
        with st.expander("📋 Vis flere detaljer (Name, Floor, Zone)"):
            detail_cols = ['Name', 'Floor', 'Zone'] + available_cols
            detail_cols_available = [col for col in detail_cols if col in filtered_df.columns]
            st.dataframe(
                filtered_df[detail_cols_available],
                use_container_width=True,
                height=300
            )

        st.markdown("---")

        # Advanced editor (formerly edit_tab2) - now in expander for power users
        with st.expander("🔧 Avansert redigering (full tabell)", expanded=False):
            st.info("💡 Rediger gjenbruksstatus direkte i tabellen. Original IFC-data er synlig men kan ikke endres her.")

            # Editable data editor with proper column configuration - simplified
            column_config = {
                gjenbruk_col: st.column_config.SelectboxColumn(
                    "Gjenbruksstatus",
                    help="Velg gjenbruksstatus (NY/EKS/GJEN)",
                    options=["NY", "EKS", "GJEN"],
                    required=True
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

                    # Update analysis IFC directly (fast, Solibri sees changes immediately)
                    if st.session_state.current_analysis_ifc:
                        with st.spinner("Oppdaterer IFC-fil..."):
                            st.session_state.sync.update_ifc_from_dataframe(edited_df, st.session_state.current_analysis_ifc)
                        st.success("✅ Endringer lagret til IFC! Solibri vil vise oppdateringsprompt")
                    else:
                        st.success("✅ Endringer lagret i session")

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
