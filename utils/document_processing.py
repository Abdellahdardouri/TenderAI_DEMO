"""
Simplified utilities for document processing and validation.
"""

import os
import time
import streamlit as st
from typing import Optional
import fitz  # PyMuPDF
from llama_parse import LlamaParse

# Constants
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB
LLAMA_PARSE_API_KEY = "llx-3WoEmFJuB5IiDlxPm5VX2o27n82gf9gIt9dz3NbQiFMq2zqa"

# Set API key globally
os.environ["LLAMA_CLOUD_API_KEY"] = LLAMA_PARSE_API_KEY

def validate_pdf_file(uploaded_file):
    """
    Validate uploaded PDF file.
    
    Args:
        uploaded_file: Streamlit uploaded file
    
    Returns:
        uploaded_file if valid, None otherwise
    """
    if uploaded_file is None:
        return None
        
    # Check file size
    if uploaded_file.size > MAX_FILE_SIZE:
        st.error(f"Fichier trop volumineux ({uploaded_file.size/1024/1024:.1f} MB). Maximum: {MAX_FILE_SIZE/1024/1024} MB")
        return None
    
    # Check file type
    if not uploaded_file.name.lower().endswith('.pdf'):
        st.error("Seuls les fichiers PDF sont acceptés.")
        return None
        
    return uploaded_file