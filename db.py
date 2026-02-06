import os
import json
import sqlite3
import datetime
from typing import Dict, Any, Optional

class DatabaseManager:
    """
    Database manager for storing extraction results and chat history.
    """
    
    def __init__(self, db_path: str = "data/tenders.db"):
        """
        Initialize database manager.
        
        Args:
            db_path (str): Path to SQLite database
        """
        # Ensure data directory exists
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        
        # Initialize database connection
        self.conn = sqlite3.connect(db_path)
        self.cursor = self.conn.cursor()
        
        # Create tables if they don't exist
        self._create_tables()
    
    def _create_tables(self):
        """Create necessary database tables if they don't exist."""
        # Table for storing extraction results
        self.cursor.execute('''
        CREATE TABLE IF NOT EXISTS extractions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            reference TEXT,
            publication_date TEXT,
            opening_date TEXT,
            contracting_authority TEXT,
            budget TEXT,
            provisional_deposit TEXT,
            financial_offer_ht TEXT,
            financial_offer_ttc TEXT,
            main_objective TEXT,
            detailed_objectives TEXT,
            phases_deliverables TEXT,
            technical_criteria TEXT,
            document_withdrawal TEXT,
            contact_info TEXT,
            submission_deadline TEXT,
            professional_profiles TEXT,
            run_id TEXT,
            creation_date TEXT
        )
        ''')
        
        # Table for storing chat history
        self.cursor.execute('''
        CREATE TABLE IF NOT EXISTS chat_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            extraction_id INTEGER,
            role TEXT,
            content TEXT,
            timestamp TEXT,
            FOREIGN KEY (extraction_id) REFERENCES extractions(id)
        )
        ''')
        
        self.conn.commit()
    
    def save_extraction_to_json(self, results: Dict[str, str]) -> str:
        """
        Save extraction results to JSON file.
        
        Args:
            results (Dict[str, str]): Extraction results
        
        Returns:
            str: Path to JSON file
        """
        # Create output directory if it doesn't exist
        os.makedirs("output", exist_ok=True)
        
        # Generate filename with timestamp
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"output/extraction_{timestamp}.json"
        
        # Add timestamp to results
        results_with_meta = results.copy()
        results_with_meta["timestamp"] = timestamp
        
        # Write to file
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(results_with_meta, f, ensure_ascii=False, indent=2)
        
        return filename
    
    def save_extraction_to_db(self, results: Dict[str, str], run_id: Optional[str] = None) -> int:
        """
        Save extraction results to database.
        
        Args:
            results (Dict[str, str]): Extraction results
            run_id (Optional[str]): MLflow run ID
        
        Returns:
            int: ID of inserted record
        """
        try:
            # Map extraction fields to database columns
            mapping = {
                "Référence de l'appel d'offres": "reference",
                "Date de publication": "publication_date",
                "Date d'ouverture des plis": "opening_date",
                "Autorité contractante": "contracting_authority",
                "Budget total (TTC)": "budget",
                "Montant du cautionnement provisoire": "provisional_deposit",
                "Offre financière proposée (HT)": "financial_offer_ht",
                "Offre financière proposée (TTC)": "financial_offer_ttc",
                "Objectif principal du projet": "main_objective",
                "Objectifs détaillés": "detailed_objectives",
                "Phases et livrables du projet": "phases_deliverables",
                "Critères d'évaluation technique": "technical_criteria",
                "Modalités de retrait des documents": "document_withdrawal",
                "Coordonnées de contact": "contact_info",
                "Date limite de soumission": "submission_deadline",
                "Profils professionnels requis": "professional_profiles"
            }
            
            # Prepare data for insertion
            data = {}
            for field, db_col in mapping.items():
                data[db_col] = results.get(field, "")
            
            # Add run_id and creation_date
            data["run_id"] = run_id if run_id else ""
            data["creation_date"] = datetime.datetime.now().isoformat()
            
            # Build SQL query
            columns = ', '.join(data.keys())
            placeholders = ', '.join(['?' for _ in data])
            values = tuple(data.values())
            
            # Insert data
            self.cursor.execute(
                f"INSERT INTO extractions ({columns}) VALUES ({placeholders})",
                values
            )
            self.conn.commit()
            
            # Get the ID of the inserted record
            return self.cursor.lastrowid
        except Exception as e:
            import traceback
            print(f"Error saving to database: {e}")
            print(traceback.format_exc())
            # Return a default ID
            return -1
    
    def save_chat_message(self, extraction_id: int, role: str, content: str) -> int:
        """
        Save chat message to database.
        
        Args:
            extraction_id (int): ID of associated extraction
            role (str): Message role (user or assistant)
            content (str): Message content
        
        Returns:
            int: ID of inserted message
        """
        # Insert message
        self.cursor.execute(
            "INSERT INTO chat_history (extraction_id, role, content, timestamp) VALUES (?, ?, ?, ?)",
            (extraction_id, role, content, datetime.datetime.now().isoformat())
        )
        self.conn.commit()
        
        # Get the ID of the inserted message
        return self.cursor.lastrowid
    
    def get_extraction_by_id(self, extraction_id: int) -> Dict[str, Any]:
        """
        Get extraction results by ID.
        
        Args:
            extraction_id (int): Extraction ID
        
        Returns:
            Dict[str, Any]: Extraction results
        """
        # Get column names
        self.cursor.execute("PRAGMA table_info(extractions)")
        columns = [row[1] for row in self.cursor.fetchall()]
        
        # Get extraction data
        self.cursor.execute("SELECT * FROM extractions WHERE id = ?", (extraction_id,))
        row = self.cursor.fetchone()
        
        if not row:
            return {}
        
        # Convert row to dictionary
        return {columns[i]: row[i] for i in range(len(columns))}
    
    def get_chat_history(self, extraction_id: int) -> list:
        """
        Get chat history for an extraction.
        
        Args:
            extraction_id (int): Extraction ID
        
        Returns:
            list: Chat history
        """
        # Get chat messages
        self.cursor.execute(
            "SELECT role, content, timestamp FROM chat_history WHERE extraction_id = ? ORDER BY timestamp",
            (extraction_id,)
        )
        
        # Convert rows to dictionaries
        return [{"role": row[0], "content": row[1], "timestamp": row[2]} for row in self.cursor.fetchall()]
    
    def __del__(self):
        """Close database connection on object destruction."""
        if hasattr(self, 'conn') and self.conn:
            self.conn.close()