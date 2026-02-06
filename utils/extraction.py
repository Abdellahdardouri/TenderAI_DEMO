import os
import glob
import time
import shutil
import fitz  # PyMuPDF
import streamlit as st
from typing import Dict
from openai import OpenAI
from llama_parse import LlamaParse
from llama_index.core import VectorStoreIndex, Document
from llama_index.core.node_parser import SentenceSplitter

# Hardcoded API keys (for testing phase only)
OPENAI_KEY = "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"
LLAMA_PARSE_API_KEY = "llx-3WoEmFJuB5IiDlxPm5VX2o27n82gf9gIt9dz3NbQiFMq2zqa"
DEFAULT_MODEL = "gpt-4o"

# Set keys
os.environ["OPENAI_API_KEY"] = OPENAI_KEY
os.environ["LLAMA_CLOUD_API_KEY"] = LLAMA_PARSE_API_KEY

# Enhanced prompts with the missing field
prompts = {
    "Objet": (
        "Quel est l'objet principal de l'appel d'offres ? "
        "Cherche une formulation explicite comme 'objet de l'appel', 'la présente consultation a pour objet', etc."
    ),

    "Référence": (
        "Quel est le numéro de référence de l'appel d'offres ? "
        "Cherche un identifiant précédé de 'Réf.', 'N°', ou 'numéro de la consultation'."
    ),

    "Date": (
        "Quelle est la date de l'appel d'offres ? "
        "Cherche une date explicite comme 12/04/2024 ou 01-01-2025 "
    ),

    "Estimation des coûts": (
        "Quelle est l'estimation des coûts ou la valeur du marché pour cet appel d'offres en num ? "
        "Cherche les mentions comme 'montant estimé', 'coût prévisionnel', 'valeur du marché', 'budget alloué', etc."
    ),

    "Montant de la caution": (
        "Quel est le montant de la caution provisoire exigée pour cet appel d'offres en num ? "
        "Cherche une mention comme 'le montant de la caution est fixé à', 'caution provisoire', etc."
    ),

    "Maître d'Ouvrage": (
        "Quel est le Maître d'Ouvrage de cet appel d'offres ? "
        "Cherche une mention comme 'le maître d'ouvrage est', 'l'entité adjudicatrice', ou similaire."
    ),

    "Contenu Dossier": (
        "Quels sont les documents constitutifs du dossier d'appel d'offres (DAO) ? "
        "Repère les éléments comme RC, CPS, BPU, DQE, CCAG, acte d'engagement, etc."
    ),

    "Modalités de retrait": (
        "Quelles sont les modalités de retrait ou de téléchargement du dossier d'appel d'offres ? "
        "Cherche les instructions concernant le site web (e.g. marchespublics.gov.ma) ou retrait physique."
    ),

    "Contact": (
        "Quelles sont les coordonnées de contact ? "
        "Cherche une adresse email (contenant '@'), un numéro de téléphone (commençant par '+212' ou '0'), ou une adresse postale généralement en bas du document ou dans la section contact."
    ),

    "Offre Financière": (
        "Quels documents composent le pli de l'offre financière ? "
        "Cherche la liste des pièces demandées : acte d'engagement, bordereau des prix, devis estimatif, etc."
    ),

    "Offre Technique": (
        "Quels documents composent le pli de l'offre technique ? "
        "Cherche les termes comme mémoire technique, planning, moyens humains et matériels, références, certificats, etc."
    )
}

def simple_openai_check():
    """Check if OpenAI API is working"""
    try:
        client = OpenAI(api_key=OPENAI_KEY)
        client.chat.completions.create(
            model=DEFAULT_MODEL,
            messages=[{"role": "user", "content": "Test"}],
            max_tokens=15
        )
        return True
    except Exception as e:
        st.error(f"Erreur API OpenAI: {e}")
        return False

def process_uploaded_files(uploaded_files):
    """
    Process uploaded files to a clean temporary directory
    This ensures each upload session is independent
    """
    # Create a session-specific directory with timestamp
    session_dir = f"data/session_{int(time.time())}"
    os.makedirs(session_dir, exist_ok=True)
    
    # Save each file with a simple, consistent name
    saved_files = {}
    for doc_type, uploaded_file in uploaded_files.items():
        if uploaded_file is None:
            continue
            
        # Save file with clear naming convention (avis.pdf, rc.pdf, cps.pdf)
        file_path = os.path.join(session_dir, f"{doc_type}.pdf")
        with open(file_path, "wb") as f:
            f.write(uploaded_file.read())
        
        saved_files[doc_type] = file_path
    
    return session_dir, saved_files

def parse_pdfs_to_markdown(session_dir, saved_files):
    """
    Parse PDFs to markdown files with session isolation
    Only processes files from the current upload session
    """
    # Create markdown directory for this session
    md_dir = os.path.join(session_dir, "markdown")
    os.makedirs(md_dir, exist_ok=True)
    
    # Track extracted content
    all_text = ""
    all_documents = []
    
    # Process only the files from this session
    for doc_type, pdf_path in saved_files.items():
        if not pdf_path or not os.path.exists(pdf_path):
            continue
            
        file_base = os.path.basename(pdf_path)
        st.write(f"Traitement de {doc_type}...")
        
        # 1. Extract with PyMuPDF (more reliable)
        try:
            doc = fitz.open(pdf_path)
            text_content = ""
            for page_num in range(len(doc)):
                page = doc.load_page(page_num)
                text = page.get_text("text", sort=True)
                text_content += text + "\n\n"
            doc.close()
            
            if text_content.strip():
                md_path = os.path.join(md_dir, f"{doc_type}_pymupdf.md")
                with open(md_path, 'w', encoding='utf-8') as f:
                    f.write(text_content)
                
                all_text += f"\n\n### DOCUMENT {doc_type} ###\n\n" + text_content
                doc_obj = Document(text=text_content, metadata={"type": doc_type})
                all_documents.append(doc_obj)
                st.write(f"✓ Extraction PyMuPDF: {len(text_content)} caractères")
        except Exception as e:
            st.warning(f"Échec PyMuPDF pour {doc_type}: {str(e)}")
        
        # 2. Try LlamaParse if enabled (optional)
        try:
            parser = LlamaParse(api_key=LLAMA_PARSE_API_KEY, result_type="markdown")
            llama_docs = parser.load_data([pdf_path])
            
            if llama_docs and llama_docs[0].text.strip():
                llama_text = llama_docs[0].text
                md_path = os.path.join(md_dir, f"{doc_type}_llama.md")
                with open(md_path, 'w', encoding='utf-8') as f:
                    f.write(llama_text)
                
                doc_obj = Document(text=llama_text, metadata={"type": doc_type, "method": "llama"})
                all_documents.append(doc_obj)
                st.write(f"✓ Extraction LlamaParse: {len(llama_text)} caractères")
        except Exception as e:
            st.warning(f"Échec LlamaParse pour {doc_type}: {str(e)}")
    
    # Fallback if no documents were processed
    if not all_documents and all_text.strip():
        doc_obj = Document(text=all_text, metadata={"source": "combined_text"})
        all_documents.append(doc_obj)
    
    # Check if we have any usable documents
    if not all_documents:
        st.error("Échec d'extraction sur tous les documents")
        return None, None
    
    # Save the combined text
    with open(os.path.join(md_dir, "all_text.md"), 'w', encoding='utf-8') as f:
        f.write(all_text)
    
    return md_dir, all_documents

def extract_field_information(uploaded_files: Dict) -> Dict[str, str]:
    """
    Extract information from uploaded files with session isolation
    """
    # Verify OpenAI API is working
    if not simple_openai_check():
        return {"Error": "Erreur de connexion à l'API OpenAI"}
    
    results = {}
    try:
        # Process uploaded files to session directory
        with st.spinner("Traitement des fichiers téléversés..."):
            session_dir, saved_files = process_uploaded_files(uploaded_files)
            
            # Check if we have any files
            if not saved_files:
                return {"Error": "Aucun fichier valide n'a été téléversé"}
            
            # Show which files were processed
            st.write("Fichiers traités:", list(saved_files.keys()))
        
        # Parse PDFs to markdown
        with st.spinner("Extraction du texte des PDFs..."):
            md_dir, documents = parse_pdfs_to_markdown(session_dir, saved_files)
            if not documents:
                return {"Error": "Échec de l'analyse des PDFs"}
        
        # Load the combined text
        all_text_path = os.path.join(md_dir, "all_text.md")
        all_text = ""
        if os.path.exists(all_text_path):
            with open(all_text_path, 'r', encoding='utf-8') as f:
                all_text = f.read()
        
        # Create vector index
        with st.spinner("Création de l'index pour recherche..."):
            node_parser = SentenceSplitter(chunk_size=2048)
            index = VectorStoreIndex.from_documents(
                documents, 
                transformations=[node_parser]
            )
        
        # Initialize OpenAI client
        client = OpenAI(api_key=OPENAI_KEY)
        
        # Progress bar for extraction
        progress_bar = st.progress(0)
        
        # System prompt
        system_template = """
        Tu es un expert en extraction d'informations des appels d'offres marocains.
        Examine attentivement le contexte fourni pour trouver l'information demandée.
        
        Règles:
        1. Réponds UNIQUEMENT par l'information demandée, sans phrases introductives
        2. Si l'information n'est pas explicitement mentionnée, réponds "Non spécifié"
        3. Pour le "Maître d'Ouvrage", si le document concerne la "Délégation Interministérielle aux Droits de l'Homme", c'est probablement le maître d'ouvrage
        4. Ne confonds jamais les noms de fichiers ou les en-têtes de document avec le contenu réel
        """
        
        # Process each field
        for i, (field, prompt) in enumerate(prompts.items()):
            # Update progress
            progress_bar.progress((i + 1) / len(prompts))
            
            # Query the vector index
            query_engine = index.as_query_engine(similarity_top_k=5)
            response = query_engine.query(prompt)
            context = response.response if hasattr(response, 'response') else str(response)
            
            # Add complete text for better context (if needed)
            if all_text:
                context += f"\n\nTEXTE COMPLET:\n{all_text[:5000]}"
            
            # Extract with OpenAI
            chat_response = client.chat.completions.create(
                model=DEFAULT_MODEL,
                messages=[
                    {"role": "system", "content": system_template},
                    {"role": "user", "content": f"Information à extraire: {field}\n\nContexte:\n\n{context}\n\nInstructions: {prompt}"}
                ],
                temperature=0.2
            )
            
            # Store result
            results[field] = chat_response.choices[0].message.content.strip()
        
        # Complete progress
        progress_bar.progress(1.0)
        
        # Store index and paths in session state
        index_storage_path = os.path.join(session_dir, "index")
        os.makedirs(index_storage_path, exist_ok=True)
        index.storage_context.persist(persist_dir=index_storage_path)
        
        st.session_state.session_dir = session_dir
        st.session_state.md_dir = md_dir
        st.session_state.index_path = index_storage_path
        
        return results
    
    except Exception as e:
        st.error(f"Erreur: {e}")
        return {"Error": f"Erreur d'extraction: {str(e)}"}

def clear_old_sessions(max_age_hours=24):
    """
    Clean up old session directories to free up space
    Only keeps sessions from the last 24 hours
    """
    try:
        base_dir = "data"
        if not os.path.exists(base_dir):
            return
            
        current_time = time.time()
        max_age_seconds = max_age_hours * 3600
        
        for item in os.listdir(base_dir):
            if item.startswith("session_"):
                path = os.path.join(base_dir, item)
                if os.path.isdir(path):
                    # Get directory creation time
                    try:
                        dir_time = int(item.split("_")[1])
                        age = current_time - dir_time
                        
                        # Remove if older than max age
                        if age > max_age_seconds:
                            shutil.rmtree(path)
                    except (IndexError, ValueError):
                        # Can't parse timestamp from directory name
                        pass
    except Exception as e:
        # Don't fail if cleanup has issues
        pass

def map_extraction_to_database(extraction_results):
    """
    Map extraction results to database format for direct saving
    """
    from datetime import datetime, date
    
    # Helper function to parse dates
    def parse_date(date_string):
        if not date_string or date_string == "Non spécifié":
            return None
        try:
            # Try different date formats
            for fmt in ["%d/%m/%Y", "%d-%m-%Y", "%Y-%m-%d"]:
                try:
                    return datetime.strptime(date_string, fmt).date()
                except ValueError:
                    continue
            return None
        except:
            return None
    
    # Helper function to parse monetary amounts
    def parse_amount(amount_string):
        if not amount_string or amount_string == "Non spécifié":
            return None
        try:
            # If already a number, return it
            if isinstance(amount_string, (int, float)):
                return int(amount_string)
            
            # Remove common text and extract numbers
            import re
            # Extract all sequences of digits, spaces, commas, and dots
            numbers = re.findall(r'[\d\s,\.]+', str(amount_string))
            if numbers:
                # Find the largest number (usually the actual amount)
                largest_num = 0
                for num_str in numbers:
                    try:
                        # Clean the number string
                        cleaned = num_str.replace(" ", "").replace(",", "")
                        # Handle decimal points - take only the integer part
                        if "." in cleaned:
                            cleaned = cleaned.split(".")[0]
                        
                        if cleaned and cleaned.isdigit():
                            num = int(cleaned)
                            if num > largest_num:
                                largest_num = num
                    except:
                        continue
                
                if largest_num > 0:
                    return largest_num
            
            return None
        except:
            return None
    
    # Extract variables to avoid f-string backslash issues
    reference = extraction_results.get("Référence", "")
    maitre_ouvrage = extraction_results.get("Maître d'Ouvrage", "")
    
    # Map extracted fields to database columns
    db_record = {
        # Extracted fields
        "Référence AO": reference,
        "Objet de l'appel d'offre": extraction_results.get("Objet", ""),
        "Organisme émetteur": maitre_ouvrage,
        "Date de publication": parse_date(extraction_results.get("Date")),
        "Montant estimé (MAD)": parse_amount(extraction_results.get("Estimation des coûts")),
        "Caution demandée (MAD)": parse_amount(extraction_results.get("Montant de la caution")),
        
        # Company decision fields - set to None (to be filled in gestion page)
        "GO / NO GO": None,
        "Statut": None,
        "Responsable": None,
        "Complexité perçue (1-5)": None,
        "Type de mission": None,
        "Montant offert (MAD)": None,
        "Date de soumission": None,
        "Date de décision": None,
        "Motif de rejet": None,
        "Score technique (si dispo)": None,
        "Nombre de concurrents (si dispo)": None,
        "Durée du marché (mois)": None,
        "Lien vers dossier": None,
        
        # Auto-generated fields
        "Identifiant unique": f"{reference}_{maitre_ouvrage}",
        "Région / Ville": None,  # To be filled manually
        "Secteur": None,  # To be filled manually or predicted
        "Temps de traitement (jours)": None,
        "Écart montant (%)": None,
        "Historique avec MO": None
    }
    
    return db_record