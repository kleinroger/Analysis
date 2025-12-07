import sqlite3
import json
from app import db
from sqlalchemy import text, inspect

def get_table_schema(table_name=None):
    """
    Dynamically retrieves the schema of database tables using SQLAlchemy inspector.
    Includes column names, types, and foreign key relationships.
    """
    try:
        inspector = inspect(db.engine)
        # If table_name is provided, check if it exists
        all_tables = inspector.get_table_names()
        
        if table_name:
            if table_name not in all_tables:
                return f"Error: Table '{table_name}' does not exist. Available tables: {', '.join(all_tables)}"
            tables = [table_name]
        else:
            # Filter out internal tables if needed (e.g., alembic_version)
            tables = [t for t in all_tables if t != 'alembic_version']

        schema_info = ""
        for table in tables:
            schema_info += f"CREATE TABLE {table} (\n"
            
            # Columns
            columns = inspector.get_columns(table)
            pk_constraint = inspector.get_pk_constraint(table)
            pks = pk_constraint.get('constrained_columns', [])
            
            col_defs = []
            for col in columns:
                col_def = f"    {col['name']} {col['type']}"
                if col['name'] in pks:
                    col_def += " PRIMARY KEY"
                if not col['nullable']:
                    col_def += " NOT NULL"
                col_defs.append(col_def)
            
            # Foreign Keys
            fks = inspector.get_foreign_keys(table)
            for fk in fks:
                constrained_cols = ", ".join(fk['constrained_columns'])
                referred_table = fk['referred_table']
                referred_cols = ", ".join(fk['referred_columns'])
                col_defs.append(f"    FOREIGN KEY ({constrained_cols}) REFERENCES {referred_table}({referred_cols})")
                
            schema_info += ",\n".join(col_defs)
            schema_info += "\n);\n\n"
            
        return schema_info
    except Exception as e:
        return f"Error getting schema: {str(e)}"

def run_sql_query(query):
    """
    Executes a SQL query on the database and returns the results.
    """
    if not query or not isinstance(query, str):
        return "Error: Query must be a non-empty string."

    try:
        # Use SQLAlchemy connection to execute
        with db.engine.connect() as connection:
            result = connection.execute(text(query))
            
            # If it's a SELECT statement, return rows
            if query.strip().upper().startswith("SELECT"):
                rows = result.fetchall()
                if not rows:
                    return "Query executed successfully but returned no results."
                    
                columns = result.keys()
                # Limit results to prevent context overflow (e.g., 50 rows max for raw data)
                # AI should use aggregation for large datasets
                data = [dict(zip(columns, row)) for row in rows]
                
                if len(data) > 100:
                    data = data[:100]
                    return json.dumps(data, default=str, ensure_ascii=False) + "\n... (Truncated to 100 rows)"
                
                return json.dumps(data, default=str, ensure_ascii=False)
            else:
                # For UPDATE/DELETE/INSERT, commit and return success
                connection.commit()
                return json.dumps({"status": "success", "rows_affected": result.rowcount})
                
    except Exception as e:
        return f"Error executing SQL: {str(e)}"

AVAILABLE_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "get_table_schema",
            "description": "Get the schema of the database tables to understand structure and relationships. Returns CREATE TABLE statements.",
            "parameters": {
                "type": "object",
                "properties": {
                    "table_name": {
                        "type": "string",
                        "description": "Optional: The name of a specific table to inspect."
                    }
                },
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "run_sql_query",
            "description": "Execute a SQL query against the SQLite database. Can be used to SELECT, INSERT, UPDATE, or DELETE data.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "The SQL query to execute."
                    }
                },
                "required": ["query"]
            }
        }
    }
]

def execute_tool_call(name, arguments):
    if name == "get_table_schema":
        return get_table_schema(arguments.get('table_name'))
    elif name == "run_sql_query":
        query = arguments.get("query")
        return run_sql_query(query)
    else:
        return f"Unknown tool: {name}"
