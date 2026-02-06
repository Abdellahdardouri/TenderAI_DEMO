import os
import streamlit as st
from openai import OpenAI
from llama_index.core import load_index_from_storage, StorageContext
from llama_index.core.query_engine import RetrieverQueryEngine

# Hardcoded API key (for testing phase only)
OPENAI_KEY = "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"
DEFAULT_MODEL = "gpt-4o"

# Set keys
os.environ["OPENAI_API_KEY"] = OPENAI_KEY

def initialize_query_engine():
    """
    Initialize the query engine from the stored index if available
    """
    if not st.session_state.get('index_path'):
        st.error("Aucun document traité. Veuillez d'abord extraire les données dans l'onglet principal.")
        return None
    
    try:
        # Load the index from storage
        index_path = st.session_state.get('index_path')
        if not os.path.exists(index_path):
            st.error(f"Index non trouvé: {index_path}")
            return None
            
        storage_context = StorageContext.from_defaults(persist_dir=index_path)
        index = load_index_from_storage(storage_context)
        
        # Create the query engine
        retriever = index.as_retriever(similarity_top_k=3)
        query_engine = RetrieverQueryEngine.from_args(retriever=retriever)
        
        return query_engine
    except Exception as e:
        st.error(f"Erreur lors du chargement de l'index: {e}")
        return None

def check_session():
    """
    Check if a session with processed documents exists
    """
    # Check if documents have been processed
    has_processed = st.session_state.get('document_processed', False)
    has_index = st.session_state.get('index_path') and os.path.exists(st.session_state.get('index_path'))
    
    if not has_processed or not has_index:
        st.warning("Aucun document n'a été traité. Veuillez d'abord extraire les données dans l'onglet principal.")
        return False
    return True

def get_rag_response(query_engine, user_query, chat_history):
    """
    Generate a response using RAG query engine and chat history
    """
    try:
        # Get RAG context from the query engine
        response = query_engine.query(user_query)
        rag_context = response.response
        
        # Initialize OpenAI client
        client = OpenAI(api_key=OPENAI_KEY)
        
        # Build message history
        messages = [
            {"role": "system", "content": f"""
            Tu es un assistant spécialisé dans les appels d'offres marocains.
            Ton objectif est de répondre aux questions concernant les documents d'appels d'offres qui ont été traités.
            
            Règles:
            1. Réponds uniquement en te basant sur les documents fournis et ton contexte
            2. Si l'information n'est pas disponible dans le contexte, dis-le clairement
            3. Sois précis et factuel, cite les sections spécifiques si possible
            4. Exprime-toi de manière professionnelle et concise
            
            CONTEXTE EXTRAIT DES DOCUMENTS:
            {rag_context}
            """}
        ]
        
        # Add chat history
        for msg in chat_history:
            messages.append({"role": "user" if msg["is_user"] else "assistant", "content": msg["content"]})
        
        # Add current query
        messages.append({"role": "user", "content": user_query})
        
        # Get completion from OpenAI
        chat_response = client.chat.completions.create(
            model=DEFAULT_MODEL,
            messages=messages,
            temperature=0.3
        )
        
        return chat_response.choices[0].message.content
        
    except Exception as e:
        return f"Erreur lors de la génération de la réponse: {str(e)}"

def main():
    st.title("Chat avec les Documents d'Appel d'Offres")
    st.markdown("""
    Posez des questions sur les documents d'appel d'offres que vous avez téléversés.
    L'assistant utilisera les documents traités pour vous fournir des réponses précises.
    """)
    
    # Initialize chat history if it doesn't exist
    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []
    
    # Check if we have processed documents
    if not check_session():
        st.info("Accédez d'abord à l'onglet principal pour traiter vos documents.")
        return
    
    # Display document info
    with st.expander("Informations sur les documents traités"):
        if "document_data" in st.session_state and st.session_state.document_data:
            for field, value in st.session_state.document_data.items():
                if field not in ["Error", "Status"]:
                    st.markdown(f"**{field}**: {value}")
        else:
            st.write("Aucune information disponible sur les documents.")
    
    # Initialize query engine
    query_engine = initialize_query_engine()
    if not query_engine:
        return
    
    # Display chat messages
    for message in st.session_state.chat_history:
        with st.chat_message("user" if message["is_user"] else "assistant"):
            st.markdown(message["content"])
    
    # Chat input
    if user_query := st.chat_input("Posez une question sur les documents..."):
        # Add user message to chat history
        st.session_state.chat_history.append({"content": user_query, "is_user": True})
        
        # Display user message
        with st.chat_message("user"):
            st.markdown(user_query)
        
        # Generate response
        with st.spinner("Génération de la réponse..."):
            response = get_rag_response(query_engine, user_query, st.session_state.chat_history)
        
        # Add assistant response to chat history
        st.session_state.chat_history.append({"content": response, "is_user": False})
        
        # Display assistant response
        with st.chat_message("assistant"):
            st.markdown(response)
    
    # Option to clear chat history
    if st.button("Effacer l'historique de chat"):
        st.session_state.chat_history = []
        st.rerun()

if __name__ == "__main__":
    main()