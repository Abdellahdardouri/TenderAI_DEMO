import os
import streamlit as st
import mlflow
from typing import Dict, Optional

# Constants
MLFLOW_TRACKING_URI = "mlruns"
EXPERIMENT_NAME = "/Public_Tenders_RAG"
DEFAULT_MODEL = "gpt-3.5-turbo"
DEFAULT_EMBEDDING_MODEL = "text-embedding-3-small"

def setup_mlflow_tracking() -> Optional[str]:
    """
    Set up MLflow tracking and experiment.
    
    Returns:
        Optional run ID
    """
    try:
        # End any active runs (the correction est ici)
        try:
            mlflow.end_run()
        except Exception:
            pass  # Ignorer si aucun run n'est actif
        
        # Set tracking URI (local tracking)
        mlflow.set_tracking_uri(MLFLOW_TRACKING_URI)
        
        # Set the experiment
        mlflow.set_experiment(EXPERIMENT_NAME)
        
        # Start a new run (not nested)
        mlflow.start_run(nested=False)
        
        return mlflow.active_run().info.run_id
    except Exception as e:
        st.error(f"MLflow setup error: {e}")
        return None

def log_extraction_metrics(results: Dict[str, str], run_id: Optional[str] = None) -> None:
    """
    Log extraction metrics and results to MLflow.
    
    Args:
        results (Dict[str, str]): Extracted information
        run_id (Optional[str]): MLflow run ID
    """
    try:
        # Ensure we're in a run context
        with mlflow.start_run(run_id=run_id):
            # Log metrics
            metrics = {
                "fields_extracted": len(results),
                "non_empty_fields": sum(1 for value in results.values() if value and value.strip() != "Information non trouvée")
            }
            
            # Log parameters
            params = {
                "extraction_method": "RAG",
                "embedding_model": DEFAULT_EMBEDDING_MODEL,
                "llm_model": DEFAULT_MODEL
            }
            
            # Log metrics and parameters
            for metric_name, metric_value in metrics.items():
                mlflow.log_metric(metric_name, metric_value)
            
            for param_name, param_value in params.items():
                mlflow.log_param(param_name, param_value)
            
            # Log results as an artifact
            os.makedirs("mlflow_artifacts", exist_ok=True)
            results_path = "mlflow_artifacts/extraction_results.txt"
            with open(results_path, "w", encoding="utf-8") as f:
                for field, value in results.items():
                    f.write(f"{field}: {value}\n")
            
            mlflow.log_artifact(results_path)
    except Exception as e:
        st.error(f"MLflow logging error: {e}")

def log_chat_interaction(question: str, response: str, run_id: Optional[str] = None) -> None:
    """
    Log chat interaction to MLflow.
    
    Args:
        question (str): User question
        response (str): Assistant response
        run_id (Optional[str]): MLflow run ID
    """
    try:
        # Ensure we're in a run context
        with mlflow.start_run(run_id=run_id):
            # Log parameters
            mlflow.log_param("question", question[:250] + "..." if len(question) > 250 else question)
            
            # Log metrics
            metrics = {
                "question_length": len(question),
                "response_length": len(response)
            }
            
            for metric_name, metric_value in metrics.items():
                mlflow.log_metric(metric_name, metric_value)
            
            # Log interaction as an artifact
            os.makedirs("mlflow_artifacts", exist_ok=True)
            interaction_path = "mlflow_artifacts/chat_interaction.txt"
            with open(interaction_path, "w", encoding="utf-8") as f:
                f.write(f"Question: {question}\n\nResponse: {response}")
            
            mlflow.log_artifact(interaction_path)
    except Exception as e:
        st.error(f"MLflow logging error: {e}")

def log_rag_performance_metrics(query_time: float, num_chunks: int, run_id: Optional[str] = None) -> None:
    """
    Log RAG performance metrics to MLflow.
    
    Args:
        query_time (float): Time taken to process query in seconds
        num_chunks (int): Number of chunks retrieved
        run_id (Optional[str]): MLflow run ID
    """
    try:
        # Ensure we're in a run context
        with mlflow.start_run(run_id=run_id):
            mlflow.log_metric("query_time_seconds", query_time)
            mlflow.log_metric("retrieved_chunks", num_chunks)
    except Exception as e:
        st.error(f"MLflow RAG metrics logging error: {e}")

def initialize_mlflow_openai_tracking():
    """
    Initialize MLflow OpenAI tracking.
    """
    try:
        # Set up MLflow
        mlflow.set_tracking_uri(MLFLOW_TRACKING_URI)
        mlflow.set_experiment(EXPERIMENT_NAME)
        
        # Enable OpenAI autologging if supported
        try:
            if hasattr(mlflow, 'openai') and hasattr(mlflow.openai, 'autolog'):
                mlflow.openai.autolog()
                st.success("MLflow OpenAI autologging activé")
        except (AttributeError, ImportError) as e:
            st.warning(f"MLflow OpenAI autologging non disponible: {e}")
        
        return True
    except Exception as e:
        st.error(f"Erreur lors de l'initialisation du tracking MLflow OpenAI: {e}")
        return False

def tracked_openai_chat_completion(messages, model=DEFAULT_MODEL, run_id=None):
    """
    Tracked version of OpenAI chat completion.
    
    Args:
        messages: Messages for the chat completion
        model: OpenAI model to use
        run_id: MLflow run ID
    
    Returns:
        Dict: OpenAI response
    """
    try:
        from openai import OpenAI
        
        # Initialize client
        client = OpenAI()
        
        # Make API call
        response = client.chat.completions.create(
            model=model,
            messages=messages
        )
        
        # Convert response to dict for easier handling
        response_dict = {}
        
        # Extract the relevant information from the response
        if hasattr(response, 'model_dump'):
            response_dict = response.model_dump()
        else:
            # Fallback for older OpenAI SDK versions
            response_dict = {
                'choices': [
                    {
                        'index': i,
                        'message': {
                            'role': choice.message.role,
                            'content': choice.message.content
                        }
                    }
                    for i, choice in enumerate(response.choices)
                ]
            }
            
            # Add usage if available
            if hasattr(response, 'usage'):
                response_dict['usage'] = {
                    'prompt_tokens': getattr(response.usage, 'prompt_tokens', 0),
                    'completion_tokens': getattr(response.usage, 'completion_tokens', 0),
                    'total_tokens': getattr(response.usage, 'total_tokens', 0)
                }
        
        # Log basic metrics if possible
        try:
            with mlflow.start_run(run_id=run_id):
                if 'usage' in response_dict:
                    mlflow.log_metric("openai_total_tokens", response_dict['usage'].get('total_tokens', 0))
        except Exception as e:
            st.warning(f"Impossible de logger les métriques OpenAI: {e}")
        
        return response_dict
    except Exception as e:
        st.error(f"Erreur avec l'API OpenAI: {e}")
        return {"error": str(e), "choices": [{"message": {"content": f"Erreur: {e}"}}]}