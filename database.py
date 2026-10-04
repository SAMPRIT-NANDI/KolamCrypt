import sqlite3
import datetime
from pathlib import Path
import config

class DatabaseManager:
    """Manages SQLite metadata storage for files, Kolams, and fragments."""
    
    def __init__(self, db_path: str = None):
        self.db_path = Path(db_path) if db_path else config.DB_PATH
        self.init_db()

    def get_connection(self):
        """Connect to SQLite database with ROW factory."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def init_db(self):
        """Initialize SQLite database schema."""
        config.ensure_directories()
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Files table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS files (
                    file_id TEXT PRIMARY KEY,
                    filename TEXT NOT NULL,
                    file_size INTEGER NOT NULL,
                    salt_hex TEXT NOT NULL,
                    seed TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Kolam pattern metadata table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS kolam_patterns (
                    pattern_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    file_id TEXT NOT NULL,
                    seed TEXT NOT NULL,
                    pattern_image_path TEXT NOT NULL,
                    FOREIGN KEY (file_id) REFERENCES files(file_id) ON DELETE CASCADE
                )
            """)
            
            # Fragments metadata table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS fragments (
                    fragment_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    file_id TEXT NOT NULL,
                    fragment_index INTEGER NOT NULL,
                    cloud_service TEXT NOT NULL,
                    cloud_file_id TEXT NOT NULL,
                    fragment_hash TEXT NOT NULL,
                    FOREIGN KEY (file_id) REFERENCES files(file_id) ON DELETE CASCADE
                )
            """)
            
            conn.commit()

    def save_file_record(
        self, 
        file_id: str, 
        filename: str, 
        file_size: int, 
        salt_hex: str, 
        seed: str, 
        kolam_path: str, 
        fragments: list[dict]
    ):
        """Save complete encryption record (File + Kolam + Fragments)."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Insert file record
            cursor.execute(
                "INSERT INTO files (file_id, filename, file_size, salt_hex, seed) VALUES (?, ?, ?, ?, ?)",
                (file_id, filename, file_size, salt_hex, seed)
            )
            
            # Insert Kolam record
            cursor.execute(
                "INSERT INTO kolam_patterns (file_id, seed, pattern_image_path) VALUES (?, ?, ?)",
                (file_id, seed, kolam_path)
            )
            
            # Insert fragment records
            for frag in fragments:
                cursor.execute(
                    """INSERT INTO fragments 
                       (file_id, fragment_index, cloud_service, cloud_file_id, fragment_hash) 
                       VALUES (?, ?, ?, ?, ?)""",
                    (
                        file_id, 
                        frag["index"], 
                        frag["cloud_service"], 
                        frag["cloud_file_id"], 
                        frag["hash"]
                    )
                )
                
            conn.commit()

    def get_file_record(self, file_id: str) -> dict | None:
        """Fetch file metadata record along with Kolam & Fragments info."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute("SELECT * FROM files WHERE file_id = ?", (file_id,))
            file_row = cursor.fetchone()
            if not file_row:
                return None
                
            file_dict = dict(file_row)
            
            # Fetch Kolam info
            cursor.execute("SELECT * FROM kolam_patterns WHERE file_id = ?", (file_id,))
            kolam_row = cursor.fetchone()
            file_dict["kolam"] = dict(kolam_row) if kolam_row else None
            
            # Fetch Fragments
            cursor.execute("SELECT * FROM fragments WHERE file_id = ? ORDER BY fragment_index ASC", (file_id,))
            frag_rows = cursor.fetchall()
            file_dict["fragments"] = [dict(r) for r in frag_rows]
            
            return file_dict

    def list_files(self) -> list[dict]:
        """List all stored files in database."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM files ORDER BY created_at DESC")
            return [dict(row) for row in cursor.fetchall()]

    def delete_file_record(self, file_id: str) -> bool:
        """Delete file record and associated child rows."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM files WHERE file_id = ?", (file_id,))
            conn.commit()
            return cursor.rowcount > 0

# Singleton database instance
db = DatabaseManager()

if __name__ == "__main__":
    db.init_db()
    print("Database initialized successfully.")
