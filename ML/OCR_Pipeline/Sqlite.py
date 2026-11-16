import sqlite3
import pandas as pd
import datetime
import json

class Sqlite:
    def __init__(self, db_path):
        self.db_path = db_path
        self.cur = None
        self.con = None

    def __enter__(self):
        self.con = sqlite3.connect(self.db_path)
        self.cur = self.con.cursor()
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        if exc_type is None:
            self.con.commit()
        else:
            self.con.rollback()

    def create_db_schema(self):
        self.cur.execute("""
            CREATE TABLE IF NOT EXISTS pages (
	            id INTEGER PRIMARY KEY,
	            folder_id INTEGER NOT NULL,
	            subfolder_id INTEGER NOT NULL,
	            subsubfolder_id INTEGER,
	            file_id INTEGER NOT NULL,
	            img_name TEXT NOT NULL,
	            engine TEXT NOT NULL,
	            params TEXT,
	            text TEXT,
                error TEXT,
	            score REAL,
	            status TEXT NOT NULL,
	            created_at TEXT DEFAULT (datetime('now')),
	            modified_at TEXT DEFAULT (datetime('now'))
            );
        """)
        self.cur.execute("CREATE INDEX idx_pages_folder_path ON pages (folder_id, subfolder_id, subsubfolder_id);")

    def create(self, df):
        df["params"] = df["params"].apply(json.dumps)
        self.cur.executemany(f"INSERT INTO pages(folder_id, subfolder_id, subsubfolder_id, file_id, img_name, engine, params, text, error, score, status) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", df[["folder_id", "subfolder_id", "subsubfolder_id", "file_id", "img_name", "engine", "params", "text", "error", "score", "status"]].itertuples(index=False))

    def read(self, field_names_list, img_names_list):
        field_names_str = ", ".join(field_names_list)
        placeholders = ','.join('?' * len(img_names_list))
        df = pd.read_sql(f"SELECT {field_names_str} FROM pages WHERE img_name IN ({placeholders})", self.con, params=img_names_list)
        return df

    def update(self, df):
        df["params"] = df["params"].apply(json.dumps)
        df["modified_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.cur.executemany(f"UPDATE pages SET engine = ?, params = ?, text = ?, error = ?, score = ?, status = ?, modified_at = ? WHERE folder_id = ? AND subfolder_id = ? AND subsubfolder_id = ? AND file_id = ?", df[["engine", "params", "text", "error", "score", "status", "modified_at", "folder_id", "subfolder_id", "subsubfolder_id", "file_id"]].itertuples(index=False))

    def delete(self):
        self.cur.execute("DELETE FROM pages;")

    def read_folder_pages(self, field_names_list, folder_id):
        field_names_str = ", ".join(field_names_list)
        df = pd.read_sql(f"SELECT {field_names_str} FROM pages WHERE folder_id={folder_id}", self.con)
        return df