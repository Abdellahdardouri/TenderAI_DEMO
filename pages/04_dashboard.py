import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from PIL import Image
import os
import calendar
from datetime import datetime
from dotenv import load_dotenv
from supabase import create_client

# Load environment variables
load_dotenv()

# Import dashboard utilities
from utils.dashboard import (
    load_data_from_supabase,
    calculate_kpis,
    create_monthly_tenders_chart,
    create_sector_pie_chart,
    create_region_map,
    create_amount_by_organization,
    create_deposit_by_organization,
    create_duration_by_sector,
    create_top_organizations_chart,
    create_latest_tenders_table,
    create_top_strategic_tenders,
    create_rejection_reasons_chart,
    create_processing_by_consultant,
    create_complexity_vs_success_heatmap,
    create_success_rate_evolution,
    format_currency,
    format_percentage
)

# Set page config
st.set_page_config(
    page_title="Dashboard - TenderAI",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Configure the page with a dark theme
st.markdown("""
<style>
    .stApp {
        background-color: #1E1E1E;
        color: white;
    }
    .stTabs [data-baseweb="tab-list"] {
        gap: 1px;
    }
    .stTabs [data-baseweb="tab"] {
        height: 50px;
        white-space: pre-wrap;
        background-color: #2C2C2C;
        border-radius: 4px 4px 0 0;
        gap: 1px;
        padding-top: 10px;
        padding-bottom: 10px;
    }
    .stTabs [aria-selected="true"] {
        background-color: #4E8DFF;
        color: white;
    }
    div[data-testid="stMetricValue"] {
        font-size: 1.5rem;
        color: #4E8DFF;
        font-weight: bold;
    }
    div[data-testid="stMetricLabel"] {
        font-size: 0.8rem;
        color: #B0B0B0;
    }
    div[data-testid="stMetricDelta"] {
        font-size: 0.8rem;
    }
    .stDataFrame {
        background-color: #2C2C2C;
    }
</style>
""", unsafe_allow_html=True)

# Display logo in sidebar if it exists
st.sidebar.title("TenderAI")
try:
    logo_path = "static/costhouse.png"
    if os.path.exists(logo_path):
        logo = Image.open(logo_path)
        st.sidebar.image(logo, width=200)
except Exception as e:
    st.sidebar.info("Logo non trouvé. L'application fonctionne normalement.")

# Page title
st.title("📊 Dashboard d'analyse des appels d'offres")

# Load and prepare data from Supabase
with st.spinner("Chargement des données depuis Supabase..."):
    try:
        df = load_data_from_supabase()
        if not df.empty:
            st.success(f"✅ Données chargées avec succès depuis Supabase ({len(df)} appels d'offres)")
        else:
            st.warning("⚠️ Aucune donnée trouvée dans la base de données")
    except Exception as e:
        st.error(f"❌ Erreur lors du chargement des données Supabase: {str(e)}")
        st.error("Vérifiez votre configuration Supabase dans le fichier .env")
        df = pd.DataFrame()  # Empty dataframe
        
    # Add an expander to view raw data
    with st.expander("Voir les données brutes"):
        if not df.empty:
            st.dataframe(df)
        else:
            st.info("Aucune donnée à afficher")
    
    # Calculate KPIs (only if data is loaded)
    if not df.empty:
        kpis = calculate_kpis(df)
    else:
        # Default KPIs to avoid errors
        kpis = {
            'total_ao': 0,
            'go_rate': 0,
            'response_rate': 0,
            'success_rate': 0,
            'avg_estimated': 0,
            'avg_offered': 0,
            'avg_price_diff': 0,
            'avg_deposit': 0,
            'avg_complexity': 0
        }

# Data export section in sidebar
st.sidebar.header("Exportation des données")
export_format = st.sidebar.selectbox(
    "Format d'exportation",
    ["CSV", "Excel"],
    key="export_format"
)

if st.sidebar.button("Exporter les données"):
    if not df.empty:
        if export_format == "CSV":
            csv = df.to_csv(index=False)
            st.sidebar.download_button(
                label="Télécharger le CSV",
                data=csv,
                file_name=f"tenderai_export_{datetime.now().strftime('%Y%m%d')}.csv",
                mime="text/csv",
            )
        else:  # Excel
            try:
                excel_file = f"tenderai_export_{datetime.now().strftime('%Y%m%d')}.xlsx"
                df.to_excel(excel_file, index=False)
                
                with open(excel_file, "rb") as f:
                    excel_data = f.read()
                
                st.sidebar.download_button(
                    label="Télécharger l'Excel",
                    data=excel_data,
                    file_name=excel_file,
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                )
                
                try:
                    os.remove(excel_file)
                except:
                    pass
            except Exception as e:
                st.sidebar.error(f"Erreur lors de l'exportation: {str(e)}")
    else:
        st.sidebar.error("Aucune donnée à exporter")
            
# Data filter sidebar section
st.sidebar.header("Filtres")

# Date range filter if dates exist in the dataframe
if 'Date de publication' in df.columns and not df.empty and not df['Date de publication'].isna().all():
    min_date = df['Date de publication'].min().date()
    max_date = df['Date de publication'].max().date()
    
    date_range = st.sidebar.date_input(
        "Période de publication",
        value=(min_date, max_date),
        min_value=min_date,
        max_value=max_date
    )
    
    if len(date_range) == 2:
        start_date, end_date = date_range
        st.sidebar.info(f"Filtrage des AO du {start_date} au {end_date}")
        
        mask = (df['Date de publication'].dt.date >= start_date) & (df['Date de publication'].dt.date <= end_date)
        filtered_df = df[mask]
        if not filtered_df.empty:
            df = filtered_df
            st.success(f"Filtre appliqué : {len(df)} AO(s) entre {start_date} et {end_date}")
        else:
            st.warning(f"Aucun AO trouvé entre {start_date} et {end_date}")

# Sector filter
if 'Secteur' in df.columns and not df.empty and len(df['Secteur'].dropna().unique()) > 0:
    sectors = ['Tous'] + sorted(df['Secteur'].dropna().astype(str).unique().tolist())
    selected_sector = st.sidebar.selectbox("Secteur", sectors)
    
    if selected_sector != 'Tous':
        st.sidebar.info(f"Filtrage sur le secteur: {selected_sector}")
        filtered_df = df[df['Secteur'].astype(str) == selected_sector]
        if not filtered_df.empty:
            df = filtered_df
            st.success(f"Filtre appliqué : {len(df)} AO(s) dans le secteur {selected_sector}")
        else:
            st.warning(f"Aucun AO trouvé dans le secteur {selected_sector}")

# Status filter
if 'Statut' in df.columns and not df.empty and len(df['Statut'].dropna().unique()) > 0:
    status_values = df['Statut'].fillna('Non défini').astype(str).unique().tolist()
    statuses = ['Tous'] + sorted(status_values)
    selected_status = st.sidebar.selectbox("Statut", statuses)
    
    if selected_status != 'Tous':
        st.sidebar.info(f"Filtrage sur le statut: {selected_status}")
        filtered_df = df[df['Statut'].astype(str) == selected_status]
        if not filtered_df.empty:
            df = filtered_df
            st.success(f"Filtre appliqué : {len(df)} AO(s) avec statut {selected_status}")
        else:
            st.warning(f"Aucun AO trouvé avec le statut {selected_status}")

# Display dashboard version info
st.sidebar.markdown("---")
st.sidebar.info("Dashboard v2.0 - TenderAI (Supabase)")

# Create tabs for the three pages of the dashboard
tab1, tab2, tab3 = st.tabs([
    "📊 Vue d'ensemble stratégique", 
    "🗺️ Analyse par secteur et région", 
    "📋 Suivi opérationnel et décisions"
])

# PAGE 1 - Strategic Overview
with tab1:
    st.header("Vue d'ensemble stratégique")
    
    # KPI metrics in multiple columns
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric(label="Nombre total d'AO", value=kpis['total_ao'])
        st.metric(label="Taux GO / NO GO", value=format_percentage(kpis['go_rate']))
    
    with col2:
        st.metric(label="Taux de réponse", value=format_percentage(kpis['response_rate']))
        st.metric(label="Taux de succès", value=format_percentage(kpis['success_rate']))
    
    with col3:
        st.metric(label="Montant estimé moyen", value=format_currency(kpis['avg_estimated']))
        st.metric(label="Montant offert moyen", value=format_currency(kpis['avg_offered']))
    
    with col4:
        st.metric(label="Écart prix moyen", value=format_percentage(kpis['avg_price_diff']))
        st.metric(label="Caution moyenne", value=format_currency(kpis['avg_deposit']))
    
    # Complexity metric in centered row
    if kpis['avg_complexity'] > 0:
        st.metric(label="Complexité moyenne (1-5)", value=f"{kpis['avg_complexity']:.2f}")
    
    # Monthly tenders histogram
    st.subheader("Appels d'offres traités par mois")
    monthly_chart = create_monthly_tenders_chart(df)
    st.plotly_chart(monthly_chart, use_container_width=True, key="monthly_chart")
    
    # Success rate evolution over time
    st.subheader("Évolution du taux de succès")
    success_evolution = create_success_rate_evolution(df)
    st.plotly_chart(success_evolution, use_container_width=True, key="success_evolution_chart")

# PAGE 2 - Sector and Regional Analysis
with tab2:
    st.header("Analyse par secteur et région")
    
    # Sector pie chart and Region map side by side
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("Répartition par secteur")
        sector_chart = create_sector_pie_chart(df)
        st.plotly_chart(sector_chart, use_container_width=True, key="sector_chart")
    
    with col2:
        st.subheader("Répartition par région")
        region_map = create_region_map(df)
        st.plotly_chart(region_map, use_container_width=True, key="region_map")
    
    # Amounts by organization
    st.subheader("Répartition des montants estimés par organisme")
    amount_org_chart = create_amount_by_organization(df)
    st.plotly_chart(amount_org_chart, use_container_width=True, key="amount_org_chart")
    
    # Deposits by organization
    st.subheader("Répartition des cautions par organisme")
    deposit_org_chart = create_deposit_by_organization(df)
    st.plotly_chart(deposit_org_chart, use_container_width=True, key="deposit_org_chart")
    
    # Duration by sector
    st.subheader("Durée des marchés par secteur")
    duration_chart = create_duration_by_sector(df)
    st.plotly_chart(duration_chart, use_container_width=True, key="duration_chart")
    
    # Top 5 organizations by amount
    st.subheader("Top 5 maîtres d'ouvrage par montant")
    top_orgs_chart = create_top_organizations_chart(df)
    st.plotly_chart(top_orgs_chart, use_container_width=True, key="top_orgs_chart")

# PAGE 3 - Operational Follow-up and Decisions
with tab3:
    st.header("Suivi opérationnel et décisions")
    
    # Latest 5 tenders
    st.subheader("5 derniers AO traités")
    latest_tenders = create_latest_tenders_table(df)
    if not latest_tenders.empty:
        if 'Message' in latest_tenders.columns:
            st.warning(latest_tenders['Message'].iloc[0])
        else:
            st.dataframe(
                latest_tenders, 
                use_container_width=True,
                hide_index=True,
                column_config={
                    "Référence AO": st.column_config.TextColumn("Référence AO", width="medium"),
                    "Montant estimé (MAD)": st.column_config.TextColumn("Montant estimé", width="medium"),
                }
            )
    else:
        st.info("Aucune donnée disponible pour afficher les derniers AO.")
    
    # Top 5 strategic tenders
    st.subheader("Top 5 AO classés par score stratégique")
    top_strategic = create_top_strategic_tenders(df)
    if not top_strategic.empty:
        if 'Message' in top_strategic.columns:
            st.warning(top_strategic['Message'].iloc[0])
        else:
            st.dataframe(
                top_strategic, 
                use_container_width=True,
                hide_index=True,
                column_config={
                    "Référence AO": st.column_config.TextColumn("Référence AO", width="medium"),
                    "Montant estimé (MAD)": st.column_config.TextColumn("Montant estimé", width="medium"),
                    "Score AO stratégique": st.column_config.NumberColumn("Score", format="%.2f", width="small"),
                }
            )
    else:
        st.info("Aucune donnée disponible pour afficher le classement stratégique.")
    
    # Rejection reasons
    st.subheader("Causes de rejet")
    rejection_chart = create_rejection_reasons_chart(df)
    st.plotly_chart(rejection_chart, use_container_width=True, key="rejection_chart")
    
    # Processing by consultant
    st.subheader("Score de traitement par consultant")
    processing_chart = create_processing_by_consultant(df)
    st.plotly_chart(processing_chart, use_container_width=True, key="processing_chart")
    
    # Complexity vs Success heatmap
    st.subheader("Relation entre complexité et réussite")
    complexity_heatmap = create_complexity_vs_success_heatmap(df)
    st.plotly_chart(complexity_heatmap, use_container_width=True, key="complexity_heatmap")