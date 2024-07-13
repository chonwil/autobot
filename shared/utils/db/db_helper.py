import os
from typing import Dict, Any, List, Optional
from contextlib import contextmanager
import threading

import psycopg2
from psycopg2 import sql
from psycopg2.pool import ThreadedConnectionPool
from dotenv import load_dotenv

class DBHelper:
    _instance = None
    _pool = None
    _local = threading.local()

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(DBHelper, cls).__new__(cls)
            cls._instance._initialize()
        return cls._instance

    def _initialize(self):
        load_dotenv()
        self._create_connection_pool()

    def _create_connection_pool(self):
        dbname = os.getenv('DB_NAME')
        user = os.getenv('DB_USER')
        password = os.getenv('DB_PASSWORD')
        host = os.getenv('DB_HOST')
        port = os.getenv('DB_PORT')

        self._pool = ThreadedConnectionPool(
            minconn=1,
            maxconn=20,  # Increased max connections
            dbname=dbname,
            user=user,
            password=password,
            host=host,
            port=port
        )

    def _get_conn(self):
        if not hasattr(self._local, 'conn'):
            self._local.conn = self._pool.getconn()
        return self._local.conn

    def _put_conn(self):
        if hasattr(self._local, 'conn'):
            self._pool.putconn(self._local.conn)
            del self._local.conn

    @contextmanager
    def get_cursor(self):
        conn = self._get_conn()
        try:
            with conn.cursor() as cur:
                yield cur
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            self._put_conn()

    def execute_query(self, query: str, params: Optional[tuple] = None) -> List[Dict[str, Any]]:
        with self.get_cursor() as cur:
            cur.execute(query, params)
            if cur.description:
                columns = [col.name for col in cur.description]
                return [dict(zip(columns, row)) for row in cur.fetchall()]
        return []

    def select_by_id(self, table_name: str, id: int) -> Optional[Dict[str, Any]]:
        query = sql.SQL("SELECT * FROM {} WHERE id = %s").format(sql.Identifier(table_name))
        results = self.execute_query(query.as_string(self._get_conn()), (id,))
        return results[0] if results else None

    def select_by_attributes(self, table_name: str, attributes: Dict[str, Any]) -> List[Dict[str, Any]]:
        placeholders = sql.SQL(', ').join(sql.Placeholder() * len(attributes))
        columns = sql.SQL(', ').join(map(sql.Identifier, attributes.keys()))
        query = sql.SQL("SELECT * FROM {} WHERE ({}) = ({})").format(
            sql.Identifier(table_name),
            columns,
            placeholders
        )
        return self.execute_query(query.as_string(self._get_conn()), tuple(attributes.values()))

    def exists(self, table_name: str, attributes: Dict[str, Any]) -> bool:
        placeholders = sql.SQL(', ').join(sql.Placeholder() * len(attributes))
        columns = sql.SQL(', ').join(map(sql.Identifier, attributes.keys()))
        query = sql.SQL("SELECT EXISTS(SELECT 1 FROM {} WHERE ({}) = ({}))").format(
            sql.Identifier(table_name),
            columns,
            placeholders
        )
        result = self.execute_query(query.as_string(self._get_conn()), tuple(attributes.values()))
        return result[0]['exists'] if result else False

    def insert(self, table_name: str, data: Dict[str, Any]) -> Optional[int]:
        columns = sql.SQL(', ').join(map(sql.Identifier, data.keys()))
        placeholders = sql.SQL(', ').join(sql.Placeholder() * len(data))
        query = sql.SQL("INSERT INTO {} ({}) VALUES ({}) RETURNING id").format(
            sql.Identifier(table_name),
            columns,
            placeholders
        )
        result = self.execute_query(query.as_string(self._get_conn()), tuple(data.values()))
        return result[0]['id'] if result else None

    def update(self, table_name: str, id: int, data: Dict[str, Any]) -> None:
        set_items = sql.SQL(', ').join(
            sql.SQL("{} = {}").format(sql.Identifier(k), sql.Placeholder())
            for k in data.keys()
        )
        query = sql.SQL("UPDATE {} SET {} WHERE id = {}").format(
            sql.Identifier(table_name),
            set_items,
            sql.Placeholder()
        )
        self.execute_query(query.as_string(self._get_conn()), tuple(data.values()) + (id,))

    def initialize_database(self, schema_path: str) -> None:
        try:
            with open(schema_path, 'r') as schema_file:
                schema_sql = schema_file.read()
            self.execute_query(schema_sql)
        except psycopg2.errors.DuplicateTable:
            raise Exception("Database already initialized")

    def __del__(self):
        if self._pool:
            self._pool.closeall()