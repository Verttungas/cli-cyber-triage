import sqlite3
import os
import json
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class DatabaseManager:
    
    def __init__(self, db_path: str = "./data/incidents.db"):
        self.db_path = db_path
        self._ensure_db_directory()
        self._init_database()
        logger.info(f"DatabaseManager inicializado con DB: {db_path}")

    def _ensure_db_directory(self):
        db_dir = os.path.dirname(self.db_path)
        if db_dir and not os.path.exists(db_dir):
            os.makedirs(db_dir)
            logger.info(f"Directorio creado: {db_dir}")
    
    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn
    
    def _init_database(self):
        conn = self._get_connection()
        cursor = conn.cursor()
        
        try:
            # Table: incidents
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS incidents (
                    incident_id TEXT PRIMARY KEY,
                    file_name TEXT,
                    file_path TEXT,
                    file_type TEXT,
                    file_size INTEGER,
                    user_email TEXT,
                    cyberhaven_data TEXT,
                    status TEXT DEFAULT 'pending',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')

            # Check for status column in incidents (migration for existing DB)
            cursor.execute("PRAGMA table_info(incidents)")
            columns = [info[1] for info in cursor.fetchall()]
            if 'status' not in columns:
                logger.info("Migrando DB: Agregando columna 'status' a incidents")
                cursor.execute("ALTER TABLE incidents ADD COLUMN status TEXT DEFAULT 'pending'")

            # Table: analysis
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS analysis (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    incident_id TEXT,
                    gemini_verdict TEXT,
                    gemini_confidence REAL,
                    gemini_reasoning TEXT,
                    gemini_raw_response TEXT,
                    processing_time REAL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (incident_id) REFERENCES incidents (incident_id)
                )
            ''')

            # Table: feedback
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS feedback (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    incident_id TEXT,
                    analysis_id INTEGER,
                    original_verdict TEXT,
                    corrected_verdict TEXT,
                    analyst_comment TEXT,
                    relevance_score REAL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (incident_id) REFERENCES incidents (incident_id),
                    FOREIGN KEY (analysis_id) REFERENCES analysis (id)
                )
            ''')

            conn.commit()
            logger.info("Base de datos inicializada correctamente")
            
        except sqlite3.Error as e:
            logger.error(f"Error inicializando base de datos: {e}")
            conn.rollback()
            raise
        finally:
            conn.close()
    
    def insert_incident(self, incident_data: Dict) -> bool:
        conn = self._get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute('''
                INSERT INTO incidents (
                    incident_id, file_name, file_path, file_type, 
                    file_size, user_email, cyberhaven_data, status
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                incident_data.get('incident_id'),
                incident_data.get('file_name'),
                incident_data.get('file_path'),
                incident_data.get('file_type'),
                incident_data.get('file_size'),
                incident_data.get('user_email'),
                json.dumps(incident_data.get('cyberhaven_data', {})) if isinstance(incident_data.get('cyberhaven_data'), dict) else incident_data.get('cyberhaven_data'),
                incident_data.get('status', 'pending')
            ))
            conn.commit()
            logger.info(f"Incidente insertado: {incident_data.get('incident_id')}")
            return True
            
        except sqlite3.IntegrityError:
            logger.warning(f"Incidente duplicado: {incident_data.get('incident_id')}")
            return False
        except sqlite3.Error as e:
            logger.error(f"Error insertando incidente: {e}")
            conn.rollback()
            return False
        finally:
            conn.close()
    
    def get_incident(self, incident_id: str) -> Optional[Dict]:
        conn = self._get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute('SELECT * FROM incidents WHERE incident_id = ?', (incident_id,))
            row = cursor.fetchone()
            return dict(row) if row else None
            
        except sqlite3.Error as e:
            logger.error(f"Error obteniendo incidente: {e}")
            return None
        finally:
            conn.close()
    
    def get_all_incidents(self, status: Optional[str] = None) -> List[Dict]:
        conn = self._get_connection()
        cursor = conn.cursor()
        try:
            query = "SELECT *, created_at as timestamp FROM incidents"
            params = []
            if status:
                query += " WHERE status = ?"
                params.append(status)
            query += " ORDER BY created_at DESC"
            
            cursor.execute(query, params)
            rows = cursor.fetchall()
            return [dict(row) for row in rows]
            
        except sqlite3.Error as e:
            logger.error(f"Error obteniendo incidentes: {e}")
            return []
        finally:
            conn.close()

    def update_incident_status(self, incident_id: str, status: str) -> bool:
        conn = self._get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("UPDATE incidents SET status = ? WHERE incident_id = ?", (status, incident_id))
            conn.commit()
            return True
        except sqlite3.Error as e:
            logger.error(f"Error updating status: {e}")
            return False
        finally:
            conn.close()

    def insert_analysis(self, analysis_data: Dict) -> int:
        conn = self._get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute('''
                INSERT INTO analysis (
                    incident_id, gemini_verdict, gemini_confidence, 
                    gemini_reasoning, gemini_raw_response, processing_time
                ) VALUES (?, ?, ?, ?, ?, ?)
            ''', (
                analysis_data.get('incident_id'),
                analysis_data.get('gemini_verdict'),
                analysis_data.get('gemini_confidence'),
                analysis_data.get('gemini_reasoning'),
                analysis_data.get('gemini_raw_response'),
                analysis_data.get('processing_time')
            ))
            conn.commit()
            analysis_id = cursor.lastrowid
            logger.info(f"Análisis insertado ID: {analysis_id} para incidente: {analysis_data.get('incident_id')}")
            return analysis_id
        except sqlite3.Error as e:
            logger.error(f"Error insertando análisis: {e}")
            conn.rollback()
            return -1
        finally:
            conn.close()

    def get_latest_analysis(self, incident_id: str) -> Optional[Dict]:
        conn = self._get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute('''
                SELECT * FROM analysis 
                WHERE incident_id = ? 
                ORDER BY created_at DESC 
                LIMIT 1
            ''', (incident_id,))
            row = cursor.fetchone()
            return dict(row) if row else None
        except sqlite3.Error as e:
            logger.error(f"Error obteniendo análisis: {e}")
            return None
        finally:
            conn.close()

    def insert_feedback(self, feedback_data: Dict) -> bool:
        conn = self._get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute('''
                INSERT INTO feedback (
                    incident_id, analysis_id, original_verdict, 
                    corrected_verdict, analyst_comment, relevance_score
                ) VALUES (?, ?, ?, ?, ?, ?)
            ''', (
                feedback_data.get('incident_id'),
                feedback_data.get('analysis_id'),
                feedback_data.get('original_verdict'),
                feedback_data.get('corrected_verdict'),
                feedback_data.get('analyst_comment'),
                feedback_data.get('relevance_score')
            ))
            conn.commit()
            logger.info(f"Feedback insertado para incidente: {feedback_data.get('incident_id')}")
            return True
        except sqlite3.Error as e:
            logger.error(f"Error insertando feedback: {e}")
            conn.rollback()
            return False
        finally:
            conn.close()

    def get_feedback_for_rag(self, limit: int = 5) -> List[Dict]:
        conn = self._get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute('''
                SELECT f.*, i.file_name, i.file_type, a.gemini_reasoning as original_reasoning
                FROM feedback f
                JOIN incidents i ON f.incident_id = i.incident_id
                LEFT JOIN analysis a ON f.analysis_id = a.id
                ORDER BY f.relevance_score DESC, f.created_at DESC
                LIMIT ?
            ''', (limit,))
            rows = cursor.fetchall()
            return [dict(row) for row in rows]
        except sqlite3.Error as e:
            logger.error(f"Error obteniendo feedback para RAG: {e}")
            return []
        finally:
            conn.close()

    def get_feedback_stats(self) -> Dict:
        conn = self._get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute('SELECT COUNT(*) as total FROM feedback')
            total = cursor.fetchone()['total']
            
            cursor.execute('SELECT COUNT(*) as corrections FROM feedback WHERE original_verdict != corrected_verdict')
            corrections = cursor.fetchone()['corrections']
            
            return {
                "total_feedback": total,
                "corrections": corrections
            }
        except sqlite3.Error as e:
            logger.error(f"Error obteniendo estadísticas: {e}")
            return {"total_feedback": 0, "corrections": 0}
        finally:
            conn.close()

    def get_database_stats(self) -> Dict:
        conn = self._get_connection()
        cursor = conn.cursor()
        stats = {}
        try:
            # Incidents by status
            cursor.execute("SELECT status, COUNT(*) as count FROM incidents GROUP BY status")
            stats['incidents_by_status'] = {row['status']: row['count'] for row in cursor.fetchall()}
            
            # Total analyses
            cursor.execute("SELECT COUNT(*) as count FROM analysis")
            stats['total_analyses'] = cursor.fetchone()['count']
            
            # Total feedback
            cursor.execute("SELECT COUNT(*) as count FROM feedback")
            stats['total_feedback'] = cursor.fetchone()['count']
            
            # AI Accuracy (based on feedback where original == corrected)
            cursor.execute("SELECT COUNT(*) as total FROM feedback")
            total_fb = cursor.fetchone()['total']
            if total_fb > 0:
                cursor.execute("SELECT COUNT(*) as correct FROM feedback WHERE original_verdict = corrected_verdict")
                correct_fb = cursor.fetchone()['correct']
                stats['ai_accuracy'] = (correct_fb / total_fb) * 100
            else:
                stats['ai_accuracy'] = 0.0

            # Avg relevance
            cursor.execute("SELECT AVG(relevance_score) as avg_rel FROM feedback")
            avg_rel = cursor.fetchone()['avg_rel']
            stats['avg_relevance'] = avg_rel if avg_rel else 0.0
            
            return stats
        except sqlite3.Error as e:
            logger.error(f"Error getting stats: {e}")
            return {}
        finally:
            conn.close()

    def clear_old_data(self, days: int = 30) -> Tuple[int, int, int]:
        conn = self._get_connection()
        cursor = conn.cursor()
        try:
            date_limit = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d %H:%M:%S')
            
            # Delete feedback
            cursor.execute("DELETE FROM feedback WHERE created_at < ?", (date_limit,))
            deleted_feedback = cursor.rowcount
            
            # Delete analysis
            cursor.execute("DELETE FROM analysis WHERE created_at < ?", (date_limit,))
            deleted_analysis = cursor.rowcount
            
            # Delete incidents
            cursor.execute("DELETE FROM incidents WHERE created_at < ?", (date_limit,))
            deleted_incidents = cursor.rowcount
            
            conn.commit()
            return (deleted_incidents, deleted_analysis, deleted_feedback)
        except sqlite3.Error as e:
            logger.error(f"Error clearing old data: {e}")
            conn.rollback()
            return (0, 0, 0)
        finally:
            conn.close()