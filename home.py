import streamlit as st
import os
import nest_asyncio
from PIL import Image
from utils.initialize import * # Import initialization module first
from utils.mlflow_logger import initialize_mlflow_openai_tracking

# Load your logo
try:
    logo = Image.open("static/costhouse.png")
except FileNotFoundError:
    # Create a placeholder logo
    import numpy as np
    logo_array = np.zeros((100, 300, 3), dtype=np.uint8)
    logo_array[:, :, 0] = 100  # Add some blue
    logo_array[:, :, 1] = 150  # Add some green
    logo = Image.fromarray(logo_array)
    os.makedirs("static", exist_ok=True)
    logo.save("static/costhouse.png")

# MUST be first Streamlit call
st.set_page_config(
    page_title="TenderAI – Traitement des appels d'Offres publics",
    page_icon=logo,
    layout="wide",
    initial_sidebar_state="expanded"
)

# Apply nest_asyncio to fix event loop issues
nest_asyncio.apply()

# Initialize MLflow and OpenAI tracking
initialize_mlflow_openai_tracking()

# Initialize session state variables for document tracking
if 'document_processed' not in st.session_state:
    st.session_state.document_processed = False

if 'document_data' not in st.session_state:
    st.session_state.document_data = {}

if 'run_id' not in st.session_state:
    st.session_state.run_id = None

if 'vector_index_paths' not in st.session_state:
    st.session_state.vector_index_paths = {}

if 'chat_history' not in st.session_state:
    st.session_state.chat_history = []

if 'chat_engine' not in st.session_state:
    st.session_state.chat_engine = None

if 'updates' not in st.session_state:
    st.session_state.updates = {}

# Display logo in sidebar
try:
    logo_path = "static/costhouse.png"
    if os.path.exists(logo_path):
        logo = Image.open(logo_path)
        st.sidebar.image(logo, width=200)
except FileNotFoundError:
    st.sidebar.warning("Logo not found. Please add 'costhouse.png' to the static folder.")

# Main page content
st.title("TenderAI - Traitement des appels d'Offres publics")
st.markdown("""
## Bienvenue dans le système d'analyse d'appels d'offres

Ce système utilise l'intelligence artificielle pour extraire les informations clés 
des documents d'appels d'offres marocains et permet de discuter avec ces documents.

### Fonctionnalités

- **Extraction d'informations**: Téléversez les documents d'appel d'offres (RC, CPS, Avis) 
  pour extraire automatiquement les informations importantes.
  
- **Discussion avec les documents**: Après extraction, discutez avec un assistant IA 
  qui peut répondre à vos questions spécifiques sur les documents.

- **Dashboard d'analyse**: Visualisez les tendances, statistiques et indicateurs clés 
  de vos appels d'offres à l'aide de graphiques interactifs.

- **Suivi des performances**: Toutes les interactions sont suivies avec MLflow, permettant
  d'analyser les performances et l'utilisation des API.

### Comment utiliser l'application

1. Naviguer vers la page "Extraction" pour téléverser et traiter vos documents
2. Une fois les documents traités, utilisez la page "Chatbot" pour poser vos questions
3. Utilisez la page "Dashboard" pour analyser vos données d'appels d'offres
4. Consultez les métriques détaillées dans MLflow UI pour suivre les performances

Utilisez le menu de navigation à gauche pour naviguer entre les pages.
""")

# Navigation buttons to other pages
st.subheader("Navigation rapide")
col1, col2, col3 = st.columns(3)

with col1:
    if st.button("🔍 Extraction des documents", use_container_width=True):
        st.switch_page("pages/01_Extraction.py")

with col2:
    if st.button("💬 Chatbot", use_container_width=True):
        st.switch_page("pages/02_Chatbot.py")

with col3:
    if st.button("📊 Dashboard", use_container_width=True):
        st.switch_page("pages/03_Dashboard.py")

# Display document processing status
if st.session_state.document_processed:
    st.success("✅ Documents traités avec succès! Vous pouvez maintenant utiliser le chatbot.")
    
    # Display MLflow experiment info if available
    if st.session_state.run_id:
        st.info(f"Session MLflow active avec ID: {st.session_state.run_id}")
else:
    st.info("ℹ️ Veuillez d'abord traiter les documents dans la page Extraction.")

# Add metrics section
with st.expander("Statistiques d'utilisation", expanded=False):
    st.markdown("""
    ### Métriques suivies par MLflow
    
    - **Métriques d'extraction**:
      - Temps de traitement des documents
      - Nombre de champs extraits
      - Qualité des extractions
    
    - **Métriques de RAG**:
      - Temps de requête
      - Nombre de chunks récupérés
      - Utilisation de tokens OpenAI
    
    - **Métriques de conversation**:
      - Longueur des questions/réponses
      - Temps de réponse
      - Nombre de tours de conversation

    - **Métriques d'analyse**:
      - Budget total des appels d'offres
      - Taux de réussite (Go vs No-Go)
      - Distribution par catégorie de projet
    """)

# Display version and updated information
st.sidebar.markdown("---")
st.sidebar.info("**TenderAI v2.0**\nMise à jour: Mai 2025\nOptimisé avec LlamaIndex et FlagEmbedding")