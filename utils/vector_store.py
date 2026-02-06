import os
import glob
import streamlit as st
from typing import Dict, Any, List, Optional
from llama_index.core import SimpleDirectoryReader, VectorStoreIndex, StorageContext, load_index_from_storage
from llama_index.embeddings.openai import OpenAIEmbedding
from llama_index.llms.openai import OpenAI as LlamaIndexOpenAI
from llama_index.core.storage.docstore import SimpleDocumentStore
from llama_index.core import Settings

def create_vector_index(md_path: str) -> Optional[VectorStoreIndex]:
    """
    Build vector store index from markdown document and persist it.
    
    Args:
        md_path (str): Path to markdown file
        
    Returns:
        VectorStoreIndex: Indexed document or None if error
    """
    try:
        # Check if file exists
        if not os.path.exists(md_path):
            st.error(f"File does not exist: {md_path}")
            return None
            
        # Initialize embedding model and LLM
        embed_model = OpenAIEmbedding(model="text-embedding-3-small")
        llm = LlamaIndexOpenAI(model="gpt-3.5-turbo")
        
        # Set global settings
        Settings.llm = llm
        Settings.embed_model = embed_model
        
        # Extract document name from path
        file_name = os.path.basename(md_path)
        doc_name = file_name.split('_')[0] if '_' in file_name else 'unknown'
        persist_dir = f"data/indices/{doc_name}"
        
        # Check if index already exists
        if os.path.exists(persist_dir):
            try:
                # Load existing index
                storage_context = StorageContext.from_defaults(persist_dir=persist_dir)
                return load_index_from_storage(storage_context)
            except Exception as e:
                st.warning(f"Failed to load existing index: {e}. Recreating...")
                # Continue to recreate the index
        
        # Create directory if not exists
        os.makedirs(persist_dir, exist_ok=True)
        
        # Load documents
        docs = SimpleDirectoryReader(input_files=[md_path]).load_data()
        
        if not docs:
            st.warning(f"No content found in {md_path}")
            return None
        
        # Create index
        index = VectorStoreIndex.from_documents(
            docs, 
            show_progress=True
        )
        
        # Persist index
        index.storage_context.persist(persist_dir=persist_dir)
        
        return index
    except Exception as e:
        import traceback
        st.error(f"Error creating vector index for {md_path}: {e}")
        st.error(traceback.format_exc())
        return None

def load_vector_indices(index_paths: Dict[str, str]) -> Dict[str, VectorStoreIndex]:
    """
    Load vector indices from persisted storage.
    
    Args:
        index_paths (Dict[str, str]): Paths to markdown files
        
    Returns:
        Dict[str, VectorStoreIndex]: Loaded indices
    """
    indices = {}
    
    # Initialize embed model and LLM
    embed_model = OpenAIEmbedding(model="text-embedding-3-small")
    llm = LlamaIndexOpenAI(model="gpt-3.5-turbo")
    
    # Set global settings
    Settings.llm = llm
    Settings.embed_model = embed_model
    
    for name, path in index_paths.items():
        if not path or not os.path.exists(path):
            st.warning(f"Invalid path for {name}: {path}")
            continue
            
        # Get the persist directory
        file_name = os.path.basename(path)
        doc_name = file_name.split('_')[0] if '_' in file_name else name
        persist_dir = f"data/indices/{doc_name}"
        
        if os.path.exists(persist_dir):
            try:
                # Load existing index
                storage_context = StorageContext.from_defaults(persist_dir=persist_dir)
                indices[name] = load_index_from_storage(storage_context)
                st.success(f"Loaded index for {name}")
            except Exception as e:
                st.warning(f"Failed to load existing index for {name}: {e}. Creating new index...")
                # Create new index
                new_index = create_vector_index(path)
                if new_index:
                    indices[name] = new_index
        else:
            # Create new index
            new_index = create_vector_index(path)
            if new_index:
                indices[name] = new_index
    
    return indices