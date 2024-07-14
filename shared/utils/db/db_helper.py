import os
from typing import Dict, Any, List, Optional, Union
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
            cls._instance = super().__new__(cls)
            cls._instance._initialize()
        return cls._instance

    def _initialize(self):
        load_dotenv()
        self._create_connection_pool()

    def _create_connection_pool(self):
        config = {
            'dbname': os.getenv('DB_NAME'),
            'user': os.getenv('DB_USER'),
            'password': os.getenv('DB_PASSWORD'),
            'host': os.getenv('DB_HOST'),
            'port': os.getenv('DB_PORT')
        }
        self._pool = ThreadedConnectionPool(minconn=1, maxconn=20, **config)

    @contextmanager
    def get_cursor(self):
        conn = self._pool.getconn()
        try:
            with conn.cursor() as cur:
                yield cur
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            self._pool.putconn(conn)

    def execute_query(self, query: Union[str, sql.Composed], params: Optional[tuple] = None) -> List[Dict[str, Any]]:
        with self.get_cursor() as cur:
            cur.execute(query, params)
            if cur.description:
                columns = [col.name for col in cur.description]
                return [dict(zip(columns, row)) for row in cur.fetchall()]
        return []

    def _build_conditions(self, attributes: Dict[str, Any]) -> sql.Composed:
        return sql.SQL(' AND ').join(
            sql.SQL("{} = {}").format(sql.Identifier(k), sql.Placeholder())
            for k in attributes
        )

    def select_by_attributes(self, table_name: str, attributes: Dict[str, Any]) -> List[Dict[str, Any]]:
        query = sql.SQL("SELECT * FROM {} WHERE {}").format(
            sql.Identifier(table_name),
            self._build_conditions(attributes)
        )
        return self.execute_query(query, tuple(attributes.values()))

    def select_by_id(self, table_name: str, primary_key: Union[str, int, Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        attributes = self._prepare_primary_key(primary_key)
        results = self.select_by_attributes(table_name, attributes)
        return results[0] if results else None

    def exists(self, table_name: str, attributes: Union[str, int, Dict[str, Any]]) -> bool:
        attributes = self._prepare_primary_key(attributes)
        query = sql.SQL("SELECT EXISTS(SELECT 1 FROM {} WHERE {})").format(
            sql.Identifier(table_name),
            self._build_conditions(attributes)
        )
        result = self.execute_query(query, tuple(attributes.values()))
        return result[0]['exists'] if result else False

    def insert(self, table_name: str, data: Dict[str, Any]) -> Union[str, int, Dict[str, Any]]:
        columns = sql.SQL(', ').join(map(sql.Identifier, data.keys()))
        placeholders = sql.SQL(', ').join(sql.Placeholder() * len(data))
        query = sql.SQL("INSERT INTO {} ({}) VALUES ({}) RETURNING *").format(
            sql.Identifier(table_name), columns, placeholders
        )
        result = self.execute_query(query, tuple(data.values()))
        return result[0].get('id', result[0]) if result else None

    def update(self, table_name: str, primary_key: Union[str, int, Dict[str, Any]], data: Dict[str, Any]) -> None:
        primary_key = self._prepare_primary_key(primary_key)
        set_items = sql.SQL(', ').join(
            sql.SQL("{} = {}").format(sql.Identifier(k), sql.Placeholder())
            for k in data
        )
        query = sql.SQL("UPDATE {} SET {} WHERE {}").format(
            sql.Identifier(table_name),
            set_items,
            self._build_conditions(primary_key)
        )
        self.execute_query(query, tuple(data.values()) + tuple(primary_key.values()))

    def initialize_database(self, schema_path: str) -> None:
        with open(schema_path, 'r') as schema_file:
            schema_sql = schema_file.read()
        try:
            self.execute_query(schema_sql)
        except psycopg2.errors.DuplicateTable:
            raise Exception("Database already initialized")

    @staticmethod
    def _prepare_primary_key(primary_key: Union[str, int, Dict[str, Any]]) -> Dict[str, Any]:
        return {'id': primary_key} if isinstance(primary_key, (str, int)) else primary_key

    def __del__(self):
        if self._pool:
            self._pool.closeall()