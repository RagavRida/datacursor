"""
Database Manager - Handles database connections and schema introspection.
Supports PostgreSQL, MySQL, SQLite, and Snowflake via SQLAlchemy.
"""

import os
from typing import Dict, List, Optional, Any
from sqlalchemy import create_engine, inspect, text, Engine

class DatabaseManager:
    """Manages database connections and metadata."""
    
    def __init__(self):
        # connections: session_id -> {connection_name: engine}
        self.connections: Dict[str, Dict[str, Engine]] = {}
        
    def connect(self, session_id: str, name: str, type: str, **kwargs) -> bool:
        """
        Create a new database connection.
        
        Args:
            session_id: The user session ID
            name: Display name for the connection
            type: 'postgres', 'mysql', 'sqlite', 'snowflake'
            kwargs: Connection parameters (host, port, user, password, database)
        """
        if session_id not in self.connections:
            self.connections[session_id] = {}
            
        url = self._build_url(type, **kwargs)
        
        try:
            engine = create_engine(url)
            # Test connection
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            
            self.connections[session_id][name] = engine
            return True
        except Exception as e:
            raise Exception(f"Failed to connect: {str(e)}")

    def _build_url(self, type: str, **kwargs) -> str:
        """Build SQLAlchemy connection URL."""
        if type == "sqlite":
            path = kwargs.get("database", ":memory:")
            return f"sqlite:///{path}"
            
        user = kwargs.get("user", "")
        password = kwargs.get("password", "")
        host = kwargs.get("host", "localhost")
        port = kwargs.get("port", "")
        database = kwargs.get("database", "")
        
        auth = f"{user}:{password}" if password else user
        net = f"{host}:{port}" if port else host
        
        if type == "postgres":
            return f"postgresql://{auth}@{net}/{database}"
        elif type == "mysql":
            return f"mysql+pymysql://{auth}@{net}/{database}"
        elif type == "snowflake":
            # Snowflake requires specific format: snowflake://<user>:<password>@<account>/<database>/<schema>?warehouse=<warehouse>&role=<role>
            account = kwargs.get("account", host) # treat host as account for snowflake
            warehouse = kwargs.get("warehouse", "")
            schema = kwargs.get("schema", "PUBLIC")
            role = kwargs.get("role", "")
            
            url = f"snowflake://{auth}@{account}/{database}/{schema}"
            params = []
            if warehouse: params.append(f"warehouse={warehouse}")
            if role: params.append(f"role={role}")
            
            if params:
                url += "?" + "&".join(params)
            return url
            
        raise ValueError(f"Unsupported database type: {type}")

    def get_connections(self, session_id: str) -> List[str]:
        """List active connection names for a session."""
        return list(self.connections.get(session_id, {}).keys())

    def disconnect(self, session_id: str, name: str) -> bool:
        """Remove a connection."""
        if session_id in self.connections and name in self.connections[session_id]:
            engine = self.connections[session_id][name]
            engine.dispose()
            del self.connections[session_id][name]
            return True
        return False

    def get_schema(self, session_id: str, name: str) -> Dict[str, Any]:
        """
        Get database schema (tables and columns).
        Returns: {
            "tables": [
                {
                    "name": "table_name",
                    "columns": [{"name": "col", "type": "VARCHAR"}]
                }
            ]
        }
        """
        engine = self._get_engine(session_id, name)
        insp = inspect(engine)
        
        schema = {"tables": []}
        
        for table_name in insp.get_table_names():
            columns = []
            try:
                for col in insp.get_columns(table_name):
                    columns.append({
                        "name": col["name"],
                        "type": str(col["type"])
                    })
                
                schema["tables"].append({
                    "name": table_name,
                    "columns": columns
                })
            except Exception as e:
                # Skip tables we can't inspect (permissions etc)
                print(f"Error inspecting table {table_name}: {e}")
                continue
                
        return schema

    def preview_query(self, session_id: str, name: str, query: str) -> List[Dict[str, Any]]:
        """Execute a read-only query and return results (limited to 50 rows)."""
        engine = self._get_engine(session_id, name)
        
        # Basic SQL injection/modification prevention for preview
        # In production, use a read-only db user or robust parsing
        q_lower = query.strip().lower()
        if not q_lower.startswith("select") and not q_lower.startswith("with"):
             raise ValueError("Only SELECT queries are allowed in preview")
             
        with engine.connect() as conn:
            result = conn.execute(text(query).execution_options(no_parameters=True))
            # Limit to 50 rows
            rows = result.fetchmany(50)
            return [dict(row._mapping) for row in rows]

    def _get_engine(self, session_id: str, name: str) -> Engine:
        """Get SQLAlchemy engine or raise error."""
        if session_id not in self.connections or name not in self.connections[session_id]:
            raise ValueError(f"Database connection '{name}' not found")
        return self.connections[session_id][name]

# Global instance
db_manager = DatabaseManager()
