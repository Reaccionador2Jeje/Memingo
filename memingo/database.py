"""Project-scoped SQLite helper for Memingo."""
import sqlite3
import threading
from pathlib import Path


class MemingoSQLite:
    def __init__(self, project_directory, filename):
        if not isinstance(filename, str) or not filename:
            raise ValueError("Database path must be a non-empty string")
        if filename == ":memory:":
            target = filename
        else:
            requested = Path(filename)
            if requested.is_absolute() or ".." in requested.parts:
                raise ValueError("Database path must stay inside the project directory")
            root = Path(project_directory).resolve()
            target_path = (root / requested).resolve()
            if target_path != root and root not in target_path.parents:
                raise ValueError("Database path must stay inside the project directory")
            target_path.parent.mkdir(parents=True, exist_ok=True)
            target = str(target_path)
        self.connection = sqlite3.connect(target, check_same_thread=False)
        self.connection.row_factory = sqlite3.Row
        self.lock = threading.RLock()
        self.closed = False

    def _check_open(self):
        if self.closed:
            raise ValueError("Database connection is closed")

    def execute(self, sql, parameters=None):
        if not isinstance(sql, str) or not sql.strip():
            raise ValueError("SQL statement must be non-empty text")
        if parameters is None:
            parameters = []
        if not isinstance(parameters, (list, tuple, dict)):
            raise ValueError("SQL parameters must be a list or object")
        with self.lock:
            self._check_open()
            cursor = self.connection.execute(sql, parameters)
            self.connection.commit()
            return {"lastrowid": cursor.lastrowid, "rowcount": cursor.rowcount}

    def query(self, sql, parameters=None):
        if not isinstance(sql, str) or not sql.strip():
            raise ValueError("SQL query must be non-empty text")
        if parameters is None:
            parameters = []
        if not isinstance(parameters, (list, tuple, dict)):
            raise ValueError("SQL parameters must be a list or object")
        with self.lock:
            self._check_open()
            cursor = self.connection.execute(sql, parameters)
            return [dict(row) for row in cursor.fetchall()]

    def close(self):
        with self.lock:
            if self.closed:
                return False
            self.connection.close()
            self.closed = True
            return True

    def api(self):
        return {"execute": self.execute, "query": self.query, "close": self.close}
