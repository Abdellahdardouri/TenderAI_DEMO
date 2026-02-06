# Système RAG pour Appels d'Offres Marocains

Ce système utilise la technique de Retrieval-Augmented Generation (RAG) pour analyser les documents d'appels d'offres marocains, extraire des informations clés et permettre une interaction conversationnelle avec ces documents.

## Caractéristiques principales

- **Extraction d'informations structurées** à partir des documents RC, CPS et Avis
- **Génération de fiches de dépouillement** au format Word
- **Interface conversationnelle** pour interroger les documents
- **Traçabilité MLflow** pour le suivi des métriques d'extraction
- **Stockage en base de données** des résultats d'extraction

## Structure du projet

```
├── 📁 .streamlit/
│   └── config.toml                  # Configuration Streamlit
├── 📁 pages/
│   ├── 01_extraction.py             # Page d'extraction de documents
│   └── 02_chatbot.py                # Interface de chatbot
├── 📁 utils/
│   ├── __init__.py                  # Initialisation du package
│   ├── document_processing.py       # Traitement des documents
│   ├── extraction.py                # Extraction d'informations
│   ├── mlflow_logger.py             # Journalisation MLflow
│   └── vector_store.py              # Gestion des index vectoriels
├── 📁 static/
│   └── costhouse.png                # Logo de l'application
├── db.py                            # Gestion de la base de données
├── Home.py                          # Point d'entrée de l'application
└── requirements.txt                 # Dépendances
```

## Prérequis

- Python 3.9 ou supérieur
- Pip (gestionnaire de paquets Python)
- Clé API OpenAI
- Clé API LlamaParse

## Installation

1. Cloner ce dépôt ou télécharger les fichiers

2. Créer un environnement virtuel et l'activer :
   ```bash
   python -m venv venv
   source venv/bin/activate  # Sur Windows : venv\Scripts\activate
   ```

3. Installer les dépendances :
   ```bash
   pip install -r requirements.txt
   ```

4. Ajouter le logo de l'application :
   - Placer votre fichier `costhouse.png` dans le dossier `static/`

5. Modifier les clés API dans les fichiers :
   - `utils/document_processing.py` : Remplacer `LLAMA_KEY`
   - `utils/extraction.py` : Remplacer `OPENAI_KEY`

## Utilisation

1. Lancer l'application :
   ```bash
   streamlit run Home.py
   ```

2. Accéder à l'application dans votre navigateur (généralement à l'adresse http://localhost:8501)

3. Suivre le workflow :
   - Aller sur la page "Extraction"
   - Téléverser les documents RC, CPS et Avis
   - Lancer l'extraction
   - Une fois l'extraction terminée, naviguer vers la page "Chatbot"
   - Poser des questions sur les documents

## Résolution des problèmes courants

### Erreur : 'NoneType' object has no attribute 'items'

Cette erreur se produit lorsque la fonction d'extraction retourne `None` au lieu d'un dictionnaire. Vérifiez les points suivants :

1. Les documents PDF sont-ils valides et lisibles ?
2. Les clés API sont-elles correctes et actives ?
3. La connexion internet est-elle stable ?

### Impossible de charger les indices de documents

Vérifiez que :
1. Les documents ont été correctement traités
2. Les fichiers markdown existent dans le répertoire `data/md/`
3. Les chemins de fichiers sont correctement stockés dans `st.session_state.vector_index_paths`

## Personnalisation

### Modification des champs d'extraction

Modifiez le dictionnaire `prompts` dans `utils/extraction.py` pour ajouter, modifier ou supprimer des champs d'extraction.

### Modification du modèle LLM

Changez les constantes `DEFAULT_MODEL` et `DEFAULT_EMBEDDING_MODEL` dans `utils/extraction.py` pour utiliser différents modèles OpenAI.

### Personnalisation de l'interface

Modifiez le fichier `.streamlit/config.toml` pour changer les couleurs et le style de l'interface.

## Licence

Ce projet est distribué sous licence MIT.