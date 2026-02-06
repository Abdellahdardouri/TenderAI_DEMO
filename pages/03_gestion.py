import streamlit as st
import pandas as pd
from datetime import datetime, date
import json

# Import gestion utilities
from utils.gestion import (
    check_extraction_data,
    get_moroccan_regions,
    get_team_members,
    get_sector_options,
    calculate_derived_fields,
    save_to_database,
    load_existing_record,
    validate_form_data,
    get_client_history,
    format_currency_display,
    create_ao_reference,
    get_existing_ao_list
)

# Set page config
st.set_page_config(
    page_title="Gestion des AO - TenderAI",
    page_icon="📝",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Page title and description
st.title("📝 Gestion des Appels d'Offres")
st.markdown("""
Gérez vos appels d'offres en ajoutant les informations spécifiques à votre entreprise 
et en prenant les décisions stratégiques nécessaires.
""")

# Initialize session state
if 'form_data' not in st.session_state:
    st.session_state.form_data = {}

# Check for extraction data
extraction_data = check_extraction_data()
has_extraction = extraction_data is not None

# Sidebar for navigation and options
st.sidebar.header("Options")

# Data source selection
data_source = st.sidebar.radio(
    "Source des données",
    ["Données extraites", "Saisie manuelle", "Modifier existant"] if has_extraction else ["Saisie manuelle", "Modifier existant"]
)

# Load existing record option
if data_source == "Modifier existant":
    st.sidebar.subheader("Sélectionner un AO existant")
    
    # Get list of existing AOs
    existing_aos = get_existing_ao_list()
    
    if existing_aos:
        # Separate pending and completed AOs
        pending_aos = [ao for ao in existing_aos if not ao.get('GO / NO GO')]
        completed_aos = [ao for ao in existing_aos if ao.get('GO / NO GO')]
        
        # Create formatted options with status indicators
        ao_options = ["Sélectionner un AO..."]
        
        # Add pending decisions first with 🔴 indicator
        if pending_aos:
            ao_options.append("--- 🔴 DÉCISIONS EN ATTENTE ---")
            for ao in pending_aos:
                status_indicator = "🔴 En attente"
                ao_options.append(
                    f"🔴 {ao['Référence AO']} - {ao['Organisme émetteur']} - {format_currency_display(ao.get('Montant estimé (MAD)', 0))} - {status_indicator}"
                )
        
        # Add completed AOs with 🟢 indicator
        if completed_aos:
            ao_options.append("--- 🟢 DÉCISIONS PRISES ---")
            for ao in completed_aos:
                status_text = ao.get('Statut', 'En cours')
                ao_options.append(
                    f"🟢 {ao['Référence AO']} - {ao['Organisme émetteur']} - {format_currency_display(ao.get('Montant estimé (MAD)', 0))} - {status_text}"
                )
        
        selected_option = st.sidebar.selectbox("Liste des AO", ao_options)
        
        # Handle selection (skip separator lines)
        if selected_option != "Sélectionner un AO..." and not selected_option.startswith("---"):
            # Extract reference from selected option (remove status indicator)
            selected_ref = selected_option.split(" - ")[0].replace("🔴 ", "").replace("🟢 ", "")
            
            if st.sidebar.button("Charger cet AO"):
                existing_data = load_existing_record(selected_ref)
                if existing_data:
                    st.session_state.form_data = existing_data
                    st.sidebar.success(f"AO {selected_ref} chargé")
                    st.rerun()
                else:
                    st.sidebar.error("Erreur lors du chargement")
        
        # Show preview of selected AO
        if selected_option != "Sélectionner un AO..." and not selected_option.startswith("---"):
            selected_ref = selected_option.split(" - ")[0].replace("🔴 ", "").replace("🟢 ", "")
            selected_ao = next((ao for ao in existing_aos if ao['Référence AO'] == selected_ref), None)
            
            if selected_ao:
                # Determine completion status
                is_pending = not selected_ao.get('GO / NO GO')
                status_color = "🔴" if is_pending else "🟢"
                completion_status = "Décision en attente" if is_pending else "Traitement complet"
                
                st.sidebar.markdown("**Aperçu:**")
                st.sidebar.markdown(f"{status_color} **Statut**: {completion_status}")
                st.sidebar.markdown(f"**Ref:** {selected_ao['Référence AO']}")
                st.sidebar.markdown(f"**Client:** {selected_ao['Organisme émetteur']}")
                st.sidebar.markdown(f"**Montant:** {format_currency_display(selected_ao.get('Montant estimé (MAD)', 0))}")
                
                if selected_ao.get('Statut'):
                    st.sidebar.markdown(f"**Statut:** {selected_ao.get('Statut', 'N/A')}")
                
                if selected_ao.get('Responsable'):
                    st.sidebar.markdown(f"**Responsable:** {selected_ao.get('Responsable', 'N/A')}")
                
                if selected_ao.get('Date de publication'):
                    date_pub = selected_ao['Date de publication'][:10] if len(selected_ao['Date de publication']) > 10 else selected_ao['Date de publication']
                    st.sidebar.markdown(f"**Date pub:** {date_pub}")
                
                # Show priority message for pending decisions
                if is_pending:
                    st.sidebar.warning("⚠️ Cet AO nécessite une décision GO/NO GO")
        
        # Show summary statistics
        if pending_aos or completed_aos:
            st.sidebar.markdown("---")
            st.sidebar.markdown("**📊 Résumé:**")
            st.sidebar.markdown(f"🔴 **En attente**: {len(pending_aos)} AO(s)")
            st.sidebar.markdown(f"🟢 **Traités**: {len(completed_aos)} AO(s)")
            st.sidebar.markdown(f"📈 **Total**: {len(existing_aos)} AO(s)")
    else:
        st.sidebar.info("Aucun AO trouvé dans la base de données")
        st.sidebar.markdown("Vous pouvez:")
        st.sidebar.markdown("• Utiliser 'Saisie manuelle' pour créer le premier AO")
        st.sidebar.markdown("• Vérifier votre connexion à la base de données")

# Display data source status
if data_source == "Données extraites" and has_extraction:
    st.success("✅ Données d'extraction disponibles")
    with st.expander("Voir les données extraites"):
        st.json(extraction_data)
elif data_source == "Saisie manuelle":
    st.info("📝 Mode saisie manuelle")

# Main form
st.header("Informations de l'Appel d'Offres")

# Create two columns for better layout
col1, col2 = st.columns(2)

with col1:
    st.subheader("📋 Informations Générales")
    
    # Basic information - extracted or manual
    if has_extraction and data_source == "Données extraites":
        # Helper function to safely parse monetary amounts from text
        def safe_parse_amount(amount_text):
            if not amount_text or amount_text == "Non spécifié":
                return 0.0
            try:
                # If already a number, return it
                if isinstance(amount_text, (int, float)):
                    return float(amount_text)
                
                # Remove common text and keep only numbers
                import re
                # Extract all numbers from the text
                numbers = re.findall(r'[\d\s,\.]+', str(amount_text))
                if numbers:
                    # Take the largest number found (usually the actual amount)
                    largest_num = ""
                    for num_str in numbers:
                        # Clean the number string
                        cleaned = num_str.replace(" ", "").replace(",", "")
                        if cleaned and len(cleaned) > len(largest_num):
                            largest_num = cleaned
                    
                    if largest_num:
                        return float(largest_num)
                
                return 0.0
            except:
                return 0.0
        
        # Show extracted data as read-only with safe parsing
        ref_ao = st.text_input("Référence AO", value=extraction_data.get("Référence", ""))
        objet = st.text_area("Objet de l'appel d'offres", value=extraction_data.get("Objet", ""),  height=100)
        maitre_ouvrage = st.text_input("Maître d'Ouvrage", value=extraction_data.get("Maître d'Ouvrage", ""))
        
        # Safe parsing for amounts
        montant_estime_raw = extraction_data.get("Estimation des coûts", "")
        montant_estime = st.number_input(
            "Montant estimé (MAD)", 
            value=safe_parse_amount(montant_estime_raw), 
            
            help=f"Texte original: {montant_estime_raw}" if montant_estime_raw else None
        )
        
        caution_raw = extraction_data.get("Montant de la caution", "")
        caution = st.number_input(
            "Caution demandée (MAD)", 
            value=safe_parse_amount(caution_raw), 
            
            help=f"Texte original: {caution_raw}" if caution_raw else None
        )
        
        # Parse date if available
        date_pub = None
        if extraction_data.get("Date"):
            try:
                date_pub = datetime.strptime(extraction_data["Date"], "%d/%m/%Y").date()
            except:
                pass
        date_publication = st.date_input("Date de publication", value=date_pub)
        
    else:
        # Manual input mode
        ref_ao = st.text_input("Référence AO *", value=st.session_state.form_data.get("reference_ao", ""))
        objet = st.text_area("Objet de l'appel d'offres *", value=st.session_state.form_data.get("objet", ""), height=100)
        maitre_ouvrage = st.text_input("Organisme émetteur/Maître d'Ouvrage *", value=st.session_state.form_data.get("organisme_emetteur", ""))
        montant_estime = st.number_input("Montant estimé (MAD) *", value=st.session_state.form_data.get("montant_estime", 0.0), min_value=0.0, step=1000.0)
        caution = st.number_input("Caution demandée (MAD)", value=st.session_state.form_data.get("caution", 0.0), min_value=0.0, step=100.0)
        date_publication = st.date_input("Date de publication *", value=st.session_state.form_data.get("date_publication", date.today()))

    # Geographic information
    region_options = get_moroccan_regions()
    region_value = st.session_state.form_data.get("region", "Casablanca-Settat")
    region_index = region_options.index(region_value) if region_value in region_options else region_options.index("Casablanca-Settat")
    region = st.selectbox("Région/Ville *", region_options, index=region_index)
    
    # Sector (auto-predicted or manual)
    secteur_options = get_sector_options()
    secteur_value = st.session_state.form_data.get("secteur", "Services IT")
    secteur_index = secteur_options.index(secteur_value) if secteur_value in secteur_options else secteur_options.index("Services IT")
    secteur = st.selectbox("Secteur", secteur_options, index=secteur_index)

with col2:
    st.subheader("🏢 Décisions Entreprise")
    
    # Company-specific fields
    go_no_go_options = ["", "GO", "NO GO"]
    go_no_go_value = st.session_state.form_data.get("go_no_go", "")
    go_no_go_index = go_no_go_options.index(go_no_go_value) if go_no_go_value in go_no_go_options else 0
    go_no_go = st.selectbox("Décision GO / NO GO *", go_no_go_options, index=go_no_go_index)
    
    statut_options = ["", "En attente", "Gagné", "Perdu", "Abandonné", "Rejeté"]
    statut_value = st.session_state.form_data.get("statut", "")
    statut_index = statut_options.index(statut_value) if statut_value in statut_options else 0
    statut = st.selectbox("Statut", statut_options, index=statut_index)
    
    # Conditional field for rejection reason
    motif_rejet = ""
    if statut == "Perdu":
        motif_rejet = st.text_area("Motif de rejet", value=st.session_state.form_data.get("motif_rejet", ""))
    
    complexite_options = [1, 2, 3, 4, 5]
    complexite_value = st.session_state.form_data.get("complexite", 3)
    complexite_index = complexite_options.index(complexite_value) if complexite_value in complexite_options else complexite_options.index(3)
    complexite = st.selectbox("Complexité perçue (1-5)", complexite_options, index=complexite_index)
    
    type_mission_options = ["Service", "Fourniture", "Travaux"]
    type_mission_value = st.session_state.form_data.get("type_mission", "Service")
    type_mission_index = type_mission_options.index(type_mission_value) if type_mission_value in type_mission_options else 0
    type_mission = st.selectbox("Type de mission", type_mission_options, index=type_mission_index)
    
    responsable_options = get_team_members()
    responsable_value = st.session_state.form_data.get("responsable", responsable_options[0])
    responsable_index = responsable_options.index(responsable_value) if responsable_value in responsable_options else 0
    responsable = st.selectbox("Responsable *", responsable_options, index=responsable_index)
    
    # Financial and timing information
    st.subheader("💰 Informations Financières & Délais")
    
    montant_offert = st.number_input("Montant offert (MAD)", value=st.session_state.form_data.get("montant_offert", 0.0), min_value=0.0, step=1000.0)
    
    duree_marche = st.number_input("Durée du marché (mois)", value=st.session_state.form_data.get("duree_marche", 12), min_value=1, max_value=120, step=1)
    
    nb_concurrents = st.number_input("Nombre de concurrents", value=st.session_state.form_data.get("nb_concurrents", 0), min_value=0, max_value=50, step=1)
    
    date_soumission = st.date_input("Date de soumission", value=st.session_state.form_data.get("date_soumission"))
    
    date_decision = st.date_input("Date de décision", value=st.session_state.form_data.get("date_decision"))
    
    # Technical and additional information
    st.subheader("📊 Informations Techniques")
    
    score_technique = st.number_input("Score technique (si disponible)", value=st.session_state.form_data.get("score_technique", 0.0), min_value=0.0, max_value=100.0, step=0.1)
    
    lien_dossier = st.text_input("Lien vers dossier", value=st.session_state.form_data.get("lien_dossier", ""))

# Calculated fields display
st.header("📈 Informations Calculées")

# Get client history for this organization
if maitre_ouvrage:
    historique = get_client_history(maitre_ouvrage)
    st.info(f"**Historique avec {maitre_ouvrage}**: {historique}")

# Calculate derived fields
derived_fields = calculate_derived_fields(
    date_publication=date_publication,
    date_soumission=date_soumission,
    date_decision=date_decision,
    montant_estime=montant_estime,
    montant_offert=montant_offert,
    statut=statut,
    complexite=complexite
)

col1, col2, col3 = st.columns(3)
with col1:
    if derived_fields["temps_traitement"]:
        st.metric("Temps de traitement", f"{derived_fields['temps_traitement']} jours")

with col2:
    if derived_fields["ecart_montant"]:
        st.metric("Écart montant", f"{derived_fields['ecart_montant']:.2f}%")

with col3:
    if derived_fields["score_strategique"]:
        st.metric("Score stratégique", f"{derived_fields['score_strategique']:,.2f}")

# Save section
st.header("💾 Enregistrement")

col1, col2, col3 = st.columns(3)

with col1:
    if st.button("💾 Enregistrer", type="primary", use_container_width=True):
        # Prepare data for saving
        form_data = {
            "reference_ao": ref_ao,
            "objet": objet,
            "organisme_emetteur": maitre_ouvrage,
            "region": region,
            "secteur": secteur,
            "montant_estime": montant_estime,
            "caution": caution,
            "date_publication": date_publication,
            "go_no_go": go_no_go,
            "statut": statut,
            "motif_rejet": motif_rejet,
            "complexite": complexite,
            "type_mission": type_mission,
            "responsable": responsable,
            "montant_offert": montant_offert,
            "duree_marche": duree_marche,
            "nb_concurrents": nb_concurrents,
            "date_soumission": date_soumission,
            "date_decision": date_decision,
            "score_technique": score_technique,
            "lien_dossier": lien_dossier,
            **derived_fields
        }
        
        # Validate required fields
        validation_errors = validate_form_data(form_data)
        
        if validation_errors:
            st.error("❌ Erreurs de validation:")
            for error in validation_errors:
                st.error(f"• {error}")
        else:
            # Save to database
            success, message = save_to_database(form_data)
            
            if success:
                st.success(f"✅ {message}")
                # Clear extraction data after successful save
                if 'document_data' in st.session_state:
                    del st.session_state['document_data']
                st.balloons()
            else:
                st.error(f"❌ {message}")

with col2:
    if st.button("📊 Voir Dashboard", use_container_width=True):
        st.switch_page("pages/04_dashboard.py")

with col3:
    if st.button("🔄 Nouveau AO", use_container_width=True):
        # Clear all form data
        st.session_state.form_data = {}
        if 'document_data' in st.session_state:
            del st.session_state['document_data']
        st.rerun()

# Display help information
with st.expander("ℹ️ Aide"):
    st.markdown("""
    ### Comment utiliser cette page:
    
    **1. Source des données:**
    - **Données extraites**: Utilise les informations extraites des documents PDF
    - **Saisie manuelle**: Saisie complète des informations
    - **Modifier existant**: Charge et modifie un AO existant
    
    **2. Champs obligatoires (*):**
    - Référence AO, Objet, Organisme émetteur
    - Montant estimé, Date de publication
    - Région/Ville, Décision GO/NO GO, Responsable
    
    **3. Champs calculés automatiquement:**
    - Temps de traitement (différence entre dates)
    - Écart montant (% entre estimé et offert)
    - Score stratégique (formule basée sur montant et complexité)
    - Historique avec MO (basé sur les données existantes)
    
    **4. Conseils:**
    - Sauvegardez régulièrement votre travail
    - Les champs non remplis seront marqués comme "Non spécifié"
    - Utilisez le motif de rejet uniquement si le statut est "Perdu"
    """)