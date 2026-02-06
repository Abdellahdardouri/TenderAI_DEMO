import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime, date
import os
from supabase import create_client
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def check_extraction_data():
    """
    Check if there's extraction data available in session state
    """
    if 'document_data' in st.session_state and st.session_state.document_data:
        return st.session_state.document_data
    return None

def get_moroccan_regions():
    """
    Return list of all Moroccan regions and major cities
    """
    return [
        "Tanger-Tétouan-Al Hoceïma",
        "Oriental", 
        "Fès-Meknès",
        "Rabat-Salé-Kénitra",
        "Béni Mellal-Khénifra",
        "Casablanca-Settat",
        "Marrakech-Safi",
        "Drâa-Tafilalet",
        "Souss-Massa",
        "Guelmim-Oued Noun",
        "Laâyoune-Sakia El Hamra",
        "Dakhla-Oued Ed-Dahab",
        # Major cities
        "Casablanca",
        "Rabat",
        "Fès",
        "Marrakech",
        "Agadir",
        "Tanger",
        "Meknès",
        "Oujda",
        "Kenitra",
        "Tétouan"
    ]

def get_team_members():
    """
    Return list of team members - in real app, this could come from database
    """
    return [
        "A. El Mansouri",
        "D. Chraibi", 
        "B. Haddad",
        "C. Tazi",
        "M. Benali",
        "S. Alaoui"
    ]

def get_sector_options():
    """
    Return list of sector options for the dropdown
    """
    return [
        "Benchmark",
        "Management de transition",
        "Chantiers de compétitivité", 
        "P2P",
        "Comptabilité analytique",
        "Services IT",
        "Pilotage analytique",
        "Formations",
        "Staffing",
        "Conseil stratégique",
        "BTP",
        "Énergie"
    ]

def calculate_derived_fields(date_publication, date_soumission, date_decision, 
                           montant_estime, montant_offert, statut, complexite):
    """
    Calculate derived fields from input data
    """
    derived = {
        "temps_traitement": None,
        "ecart_montant": None,
        "score_strategique": None
    }
    
    try:
        # Calculate processing time in days
        if date_publication and date_soumission:
            if isinstance(date_publication, str):
                date_publication = datetime.strptime(date_publication, "%Y-%m-%d").date()
            if isinstance(date_soumission, str):
                date_soumission = datetime.strptime(date_soumission, "%Y-%m-%d").date()
            
            if date_soumission > date_publication:
                derived["temps_traitement"] = (date_soumission - date_publication).days
        
        # Calculate amount difference percentage
        if montant_estime and montant_offert and montant_estime > 0:
            derived["ecart_montant"] = ((montant_offert - montant_estime) / montant_estime) * 100
        
        # Calculate strategic score
        if montant_estime and statut and complexite:
            gagne_bool = 1 if statut == "Gagné" else 0
            if complexite > 0:
                derived["score_strategique"] = (montant_estime * gagne_bool) / complexite
        
    except Exception as e:
        print(f"Error calculating derived fields: {e}")
    
    return derived

def get_client_history(organisme_emetteur):
    """
    Get historical performance with a specific client from database
    """
    try:
        # Get Supabase connection
        url = os.environ.get("SUPABASE_URL")
        key = os.environ.get("SUPABASE_KEY")
        
        if not url or not key:
            return "Historique non disponible (configuration DB)"
        
        supabase = create_client(url, key)
        
        # Query historical data for this client using correct column names
        response = supabase.table("tender_ai").select('"Statut"').eq('"Organisme émetteur"', organisme_emetteur).execute()
        
        if response.data:
            statuts = [row["Statut"] for row in response.data if row["Statut"]]
            gagne_count = sum(1 for s in statuts if s == "Gagné")
            perdu_count = sum(1 for s in statuts if s == "Perdu")
            
            return f"{gagne_count} gagné(s) / {perdu_count} perdu(s)"
        else:
            return "Nouveau client"
            
    except Exception as e:
        return f"Erreur calcul historique: {str(e)}"

def validate_form_data(form_data):
    """
    Validate form data and return list of errors
    """
    errors = []
    
    # Required fields validation
    required_fields = {
        "reference_ao": "Référence AO",
        "objet": "Objet de l'appel d'offres", 
        "organisme_emetteur": "Organisme émetteur",
        "montant_estime": "Montant estimé",
        "date_publication": "Date de publication",
        "region": "Région/Ville",
        "go_no_go": "Décision GO/NO GO",
        "responsable": "Responsable"
    }
    
    for field, label in required_fields.items():
        if not form_data.get(field) or form_data[field] == "":
            errors.append(f"{label} est obligatoire")
    
    # Specific validations
    if form_data.get("montant_estime", 0) <= 0:
        errors.append("Le montant estimé doit être supérieur à 0")
    
    if form_data.get("complexite") not in [1, 2, 3, 4, 5]:
        errors.append("La complexité doit être entre 1 et 5")
    
    # Date validations
    if form_data.get("date_soumission") and form_data.get("date_publication"):
        if form_data["date_soumission"] <= form_data["date_publication"]:
            errors.append("La date de soumission doit être après la date de publication")
    
    # Reference format validation (basic)
    ref_ao = form_data.get("reference_ao", "")
    if ref_ao and len(ref_ao) < 3:
        errors.append("La référence AO doit contenir au moins 3 caractères")
    
    return errors

def save_to_database(form_data):
    """
    Save form data to Supabase database
    """
    try:
        # Get Supabase connection
        url = os.environ.get("SUPABASE_URL")
        key = os.environ.get("SUPABASE_KEY")
        
        if not url or not key:
            return False, "Configuration Supabase manquante"
        
        supabase = create_client(url, key)
        
        # Helper function to safely convert to int
        def safe_int(value):
            if value is None or value == "":
                return None
            try:
                return int(float(value))  # Convert through float first to handle decimals
            except (ValueError, TypeError):
                return None
        
        # Helper function to safely convert to float
        def safe_float(value):
            if value is None or value == "":
                return None
            try:
                return float(value)
            except (ValueError, TypeError):
                return None
        
        # Prepare data for database using actual column names with correct data types
        db_data = {
            "Référence AO": str(form_data["reference_ao"]) if form_data["reference_ao"] else None,
            "Organisme émetteur": str(form_data["organisme_emetteur"]) if form_data["organisme_emetteur"] else None,
            "Région / Ville": str(form_data["region"]) if form_data["region"] else None,
            "Montant estimé (MAD)": safe_int(form_data["montant_estime"]),
            "Caution demandée (MAD)": safe_int(form_data.get("caution", 0)),
            "Secteur": str(form_data["secteur"]) if form_data["secteur"] else None,
            "Date de publication": form_data["date_publication"].isoformat() if form_data["date_publication"] else None,
            "GO / NO GO": str(form_data["go_no_go"]) if form_data["go_no_go"] else None,
            "Date de soumission": form_data["date_soumission"].isoformat() if form_data.get("date_soumission") else None,
            "Statut": str(form_data.get("statut")) if form_data.get("statut") else None,
            "Montant offert (MAD)": safe_int(form_data.get("montant_offert")) if form_data.get("montant_offert") else None,
            "Motif de rejet": str(form_data.get("motif_rejet")) if form_data.get("motif_rejet") else None,
            "Objet de l'appel d'offre": str(form_data["objet"]) if form_data["objet"] else None,
            "Date de décision": form_data["date_decision"].isoformat() if form_data.get("date_decision") else None,
            "Identifiant unique": f"{form_data['reference_ao']}_{form_data['organisme_emetteur']}",
            "Temps de traitement (jours)": safe_int(form_data.get("temps_traitement")),
            "Écart montant (%)": safe_float(form_data.get("ecart_montant")),
            "Durée du marché (mois)": safe_int(form_data.get("duree_marche")),
            "Complexité perçue (1-5)": safe_int(form_data["complexite"]),
            "Score technique (si dispo)": safe_int(form_data.get("score_technique")),  # Changed from safe_float to safe_int
            "Nombre de concurrents (si dispo)": safe_int(form_data.get("nb_concurrents")),
            "Responsable": str(form_data["responsable"]) if form_data["responsable"] else None,
            "Type de mission": str(form_data["type_mission"]) if form_data["type_mission"] else None,
            "Historique avec MO": str(get_client_history(form_data["organisme_emetteur"])),
            "Lien vers dossier": str(form_data.get("lien_dossier")) if form_data.get("lien_dossier") else None
        }
        
        # Debug: Print data types to help identify the issue
        st.write("🔍 Debug - Data being sent to database:")
        for key, value in db_data.items():
            if value is not None:
                st.write(f"{key}: {value} (type: {type(value).__name__})")
            else:
                st.write(f"{key}: NULL")
        
        # Check if record already exists using the correct column name
        existing = supabase.table("tender_ai").select('"Référence AO"').eq('"Référence AO"', form_data["reference_ao"]).execute()
        
        if existing.data:
            # Update existing record
            response = supabase.table("tender_ai").update(db_data).eq('"Référence AO"', form_data["reference_ao"]).execute()
            return True, f"AO {form_data['reference_ao']} mis à jour avec succès"
        else:
            # Insert new record
            response = supabase.table("tender_ai").insert(db_data).execute()
            return True, f"AO {form_data['reference_ao']} enregistré avec succès"
            
    except Exception as e:
        return False, f"Erreur lors de l'enregistrement: {str(e)}"

def load_existing_record(reference_ao):
    """
    Load an existing record from database by reference
    """
    try:
        # Get Supabase connection
        url = os.environ.get("SUPABASE_URL")
        key = os.environ.get("SUPABASE_KEY")
        
        if not url or not key:
            return None
        
        supabase = create_client(url, key)
        
        # Query the record using correct column name with proper quoting
        response = supabase.table("tender_ai").select("*").eq('"Référence AO"', reference_ao).execute()
        
        if response.data:
            record = response.data[0]
            
            # Map database fields back to form fields using actual column names
            # Convert all numeric values to float to avoid type conflicts
            form_data = {
                "reference_ao": record.get("Référence AO"),
                "objet": record.get("Objet de l'appel d'offre"),
                "organisme_emetteur": record.get("Organisme émetteur"),
                "region": record.get("Région / Ville"),
                "secteur": record.get("Secteur"),
                "montant_estime": float(record.get("Montant estimé (MAD)", 0)) if record.get("Montant estimé (MAD)") else 0.0,
                "caution": float(record.get("Caution demandée (MAD)", 0)) if record.get("Caution demandée (MAD)") else 0.0,
                "date_publication": datetime.fromisoformat(record["Date de publication"]).date() if record.get("Date de publication") else None,
                "go_no_go": record.get("GO / NO GO"),
                "statut": record.get("Statut"),
                "motif_rejet": record.get("Motif de rejet"),
                "complexite": int(record.get("Complexité perçue (1-5)", 3)) if record.get("Complexité perçue (1-5)") else 3,
                "type_mission": record.get("Type de mission", "Service"),
                "responsable": record.get("Responsable"),
                "montant_offert": float(record.get("Montant offert (MAD)", 0)) if record.get("Montant offert (MAD)") else 0.0,
                "duree_marche": int(record.get("Durée du marché (mois)", 12)) if record.get("Durée du marché (mois)") else 12,
                "nb_concurrents": int(record.get("Nombre de concurrents (si dispo)", 0)) if record.get("Nombre de concurrents (si dispo)") else 0,
                "date_soumission": datetime.fromisoformat(record["Date de soumission"]).date() if record.get("Date de soumission") else None,
                "date_decision": datetime.fromisoformat(record["Date de décision"]).date() if record.get("Date de décision") else None,
                "score_technique": float(record.get("Score technique (si dispo)", 0)) if record.get("Score technique (si dispo)") else 0.0,
                "lien_dossier": record.get("Lien vers dossier")
            }
            
            return form_data
        
        return None
        
    except Exception as e:
        st.error(f"Erreur lors du chargement: {e}")
        return None

def format_currency_display(amount):
    """
    Format currency for display
    """
    if amount is None or amount == 0:
        return "Non spécifié"
    return f"{amount:,.2f} MAD"

def create_ao_reference(organisme, year=None):
    """
    Generate a new AO reference based on organisme and year
    """
    if not year:
        year = datetime.now().year
    
    # Get initials from organisme
    words = organisme.split()
    initials = "".join([word[0].upper() for word in words[:3]])  # Max 3 initials
    
    try:
        # Get next number for this organisme/year combination
        url = os.environ.get("SUPABASE_URL")
        key = os.environ.get("SUPABASE_KEY")
        
        if url and key:
            supabase = create_client(url, key)
            
            # Count existing AOs for this organisme this year
            response = supabase.table("tender_ai").select("reference_ao").ilike("reference_ao", f"AO-{initials}-{year}%").execute()
            
            count = len(response.data) + 1
            return f"AO-{initials}-{year}-{count:03d}"
        else:
            # Fallback if no DB connection
            return f"AO-{initials}-{year}-001"
            
    except Exception:
        # Fallback in case of error
        return f"AO-{initials}-{year}-001"

def get_completion_percentage(form_data):
    """
    Calculate form completion percentage
    """
    total_fields = 20  # Total number of form fields
    completed_fields = 0
    
    required_fields = ["reference_ao", "objet", "organisme_emetteur", "montant_estime", 
                      "date_publication", "region", "go_no_go", "responsable"]
    
    optional_fields = ["secteur", "caution", "statut", "motif_rejet", "complexite",
                      "type_mission", "montant_offert", "duree_marche", "nb_concurrents",
                      "date_soumission", "date_decision", "score_technique", "lien_dossier"]
    
    # Count completed required fields
    for field in required_fields:
        if form_data.get(field) and form_data[field] != "":
            completed_fields += 1
    
    # Count completed optional fields
    for field in optional_fields:
        if form_data.get(field) and form_data[field] not in [None, "", 0]:
            completed_fields += 1
    
    return min(100, int((completed_fields / total_fields) * 100))

def get_status_color(statut):
    """
    Return color for status display
    """
    colors = {
        "Gagné": "green",
        "Perdu": "red", 
        "En attente": "orange",
        "Abandonné": "gray",
        "Rejeté": "red"
    }
    return colors.get(statut, "blue")

def export_to_excel(data_list):
    """
    Export list of AO data to Excel format
    """
    try:
        df = pd.DataFrame(data_list)
        
        # Format dates
        date_columns = ["date_publication", "date_soumission", "date_decision"]
        for col in date_columns:
            if col in df.columns:
                df[col] = pd.to_datetime(df[col], errors='coerce')
        
        # Format currency columns
        currency_columns = ["montant_estime", "montant_offert", "caution"]
        for col in currency_columns:
            if col in df.columns:
                df[col] = df[col].apply(lambda x: f"{x:,.2f} MAD" if pd.notna(x) and x > 0 else "")
        
        return df
        
    except Exception as e:
        st.error(f"Erreur lors de l'export: {e}")
        return None

def search_ao_records(search_term, search_field="all"):
    """
    Search AO records in database
    """
    try:
        url = os.environ.get("SUPABASE_URL")
        key = os.environ.get("SUPABASE_KEY")
        
        if not url or not key:
            return []
        
        supabase = create_client(url, key)
        
        if search_field == "all":
            # Search across multiple fields
            response = supabase.table("tender_ai").select("*").or_(
                f"reference_ao.ilike.%{search_term}%,"
                f"organisme_emetteur.ilike.%{search_term}%,"
                f"objet_de_l_appel_d_offre.ilike.%{search_term}%"
            ).execute()
        else:
            # Search specific field
            response = supabase.table("tender_ai").select("*").ilike(search_field, f"%{search_term}%").execute()
        
        return response.data if response.data else []
        
    except Exception as e:
        st.error(f"Erreur lors de la recherche: {e}")
        return []

def get_dashboard_summary():
    """
    Get summary statistics for dashboard preview
    """
    try:
        url = os.environ.get("SUPABASE_URL")
        key = os.environ.get("SUPABASE_KEY")
        
        if not url or not key:
            return None
        
        supabase = create_client(url, key)
        
        # Get all records
        response = supabase.table("tender_ai").select("*").execute()
        
        if response.data:
            df = pd.DataFrame(response.data)
            
            summary = {
                "total_ao": len(df),
                "go_count": len(df[df["go_no_go"] == "GO"]) if "go_no_go" in df.columns else 0,
                "gagne_count": len(df[df["statut"] == "Gagné"]) if "statut" in df.columns else 0,
                "en_cours": len(df[df["statut"] == "En attente"]) if "statut" in df.columns else 0,
                "total_value": df["montant_estime_mad"].sum() if "montant_estime_mad" in df.columns else 0
            }
            
            return summary
        
        return None
        
    except Exception as e:
        return None

def duplicate_ao_record(reference_ao, new_reference):
    """
    Duplicate an existing AO record with new reference
    """
    try:
        # Load existing record
        existing_data = load_existing_record(reference_ao)
        
        if not existing_data:
            return False, "AO source non trouvé"
        
        # Modify for new record
        existing_data["reference_ao"] = new_reference
        existing_data["statut"] = ""  # Reset status
        existing_data["date_soumission"] = None  # Reset submission date
        existing_data["date_decision"] = None  # Reset decision date
        existing_data["motif_rejet"] = ""  # Reset rejection reason
        existing_data["score_technique"] = 0  # Reset technical score
        
        # Save as new record
        success, message = save_to_database(existing_data)
        
        return success, message
        
    except Exception as e:
        return False, f"Erreur lors de la duplication: {str(e)}"

def get_existing_ao_list():
    """
    Get list of all existing AO records for selection, prioritizing pending decisions
    """
    try:
        url = os.environ.get("SUPABASE_URL")
        key = os.environ.get("SUPABASE_KEY")
        
        if not url or not key:
            return []
        
        supabase = create_client(url, key)
        
        # Use actual column names with priority ordering: pending decisions first
        response = supabase.table("tender_ai").select(
            '"Référence AO", "Organisme émetteur", "Statut", "Date de publication", '
            '"Montant estimé (MAD)", "Responsable", "Secteur", "Région / Ville", "GO / NO GO"'
        ).order('"GO / NO GO"', desc=False, nullsfirst=True).order('"Date de publication"', desc=True).execute()
        
        return response.data if response.data else []
        
    except Exception as e:
        st.sidebar.error(f"❌ Erreur lors de la récupération des AO: {e}")
        return []

def get_recent_ao_list(limit=10):
    """
    Get list of recent AO records
    """
    try:
        url = os.environ.get("SUPABASE_URL")
        key = os.environ.get("SUPABASE_KEY")
        
        if not url or not key:
            return []
        
        supabase = create_client(url, key)
        
        response = supabase.table("tender_ai").select(
            "reference_ao, organisme_emetteur, statut, date_de_publication, montant_estime_mad"
        ).order("created_at", desc=True).limit(limit).execute()
        
        return response.data if response.data else []
        
    except Exception as e:
        return []

def validate_unique_reference(reference_ao, exclude_id=None):
    """
    Check if AO reference is unique in database
    """
    try:
        url = os.environ.get("SUPABASE_URL")
        key = os.environ.get("SUPABASE_KEY")
        
        if not url or not key:
            return True  # Allow if can't check
        
        supabase = create_client(url, key)
        
        query = supabase.table("tender_ai").select("id").eq("reference_ao", reference_ao)
        
        if exclude_id:
            query = query.neq("id", exclude_id)
        
        response = query.execute()
        
        return len(response.data) == 0  # True if unique
        
    except Exception as e:
        return True  # Allow if error checking

def calculate_win_rate_by_responsable():
    """
    Calculate win rate for each team member
    """
    try:
        url = os.environ.get("SUPABASE_URL")
        key = os.environ.get("SUPABASE_KEY")
        
        if not url or not key:
            return {}
        
        supabase = create_client(url, key)
        
        response = supabase.table("tender_ai").select("responsable, statut").execute()
        
        if response.data:
            df = pd.DataFrame(response.data)
            
            # Calculate win rates
            win_rates = {}
            for responsable in df["responsable"].unique():
                if pd.notna(responsable):
                    resp_data = df[df["responsable"] == responsable]
                    total = len(resp_data[resp_data["statut"].notna()])
                    wins = len(resp_data[resp_data["statut"] == "Gagné"])
                    
                    if total > 0:
                        win_rates[responsable] = {
                            "win_rate": (wins / total) * 100,
                            "total_ao": total,
                            "wins": wins
                        }
            
            return win_rates
        
        return {}
        
    except Exception as e:
        return {}

def get_sector_distribution():
    """
    Get distribution of AOs by sector
    """
    try:
        url = os.environ.get("SUPABASE_URL")
        key = os.environ.get("SUPABASE_KEY")
        
        if not url or not key:
            return {}
        
        supabase = create_client(url, key)
        
        response = supabase.table("tender_ai").select("secteur").execute()
        
        if response.data:
            df = pd.DataFrame(response.data)
            distribution = df["secteur"].value_counts().to_dict()
            return distribution
        
        return {}
        
    except Exception as e:
        return {}