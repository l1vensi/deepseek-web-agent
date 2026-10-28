import sys
import json
import sqlite3
from pathlib import Path

# Ensure UTF-8 stdio
if sys.platform == "win32":
    try:
        sys.stdin.reconfigure(encoding='utf-8')
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

def execute_query(db_path: str, query: str):
    """Executes a SQL query against an SQLite database and returns the result."""
    p = Path(db_path)
    try:
        p.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(str(p))
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.execute(query)
        if query.strip().upper().startswith("SELECT") or query.strip().upper().startswith("PRAGMA"):
            rows = [dict(row) for row in cur.fetchall()]
            conn.close()
            return {"db": str(p), "rows_count": len(rows), "rows": rows}
        else:
            conn.commit()
            affected = cur.rowcount
            conn.close()
            return {"db": str(p), "status": "success", "rows_affected": affected}
    except Exception as e:
        return {"db": str(p), "error": str(e)}

def list_tables(db_path: str):
    """Lists all tables and views in the specified SQLite database."""
    p = Path(db_path)
    if not p.exists():
        return {"error": f"База данных не существует: {p}"}
    try:
        conn = sqlite3.connect(str(p))
        cur = conn.cursor()
        cur.execute("SELECT name, sql FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%';")
        tables = [{"name": row[0], "schema": row[1]} for row in cur.fetchall()]
        conn.close()
        return {"db": str(p), "tables": tables}
    except Exception as e:
        return {"error": str(e)}

TOOLS = [
    {
        "name": "execute_query",
        "description": "Выполняет SQL-запрос к локальной базе данных SQLite (SELECT, INSERT, CREATE TABLE, UPDATE).",
        "inputSchema": {
            "type": "object",
            "properties": {
                "db_path": {"type": "string", "description": "Путь к файлу .db"},
                "query": {"type": "string", "description": "SQL-запрос"}
            },
            "required": ["db_path", "query"]
        }
    },
    {
        "name": "list_tables",
        "description": "Показывает список таблиц и их схемы в базе данных SQLite.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "db_path": {"type": "string", "description": "Путь к файлу .db"}
            },
            "required": ["db_path"]
        }
    }
]

def main():
    while True:
        line = sys.stdin.readline()
        if not line:
            break
        line = line.strip()
        if not line:
            continue
        try:
            req = json.loads(line)
        except Exception:
            continue

        req_id = req.get("id")
        method = req.get("method")
        params = req.get("params", {})

        if method == "initialize":
            resp = {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {"tools": {}},
                    "serverInfo": {"name": "sqlite-mcp", "version": "1.0.0"}
                }
            }
            sys.stdout.write(json.dumps(resp, ensure_ascii=False) + "\n")
            sys.stdout.flush()

        elif method == "notifications/initialized":
            pass

        elif method == "tools/list":
            resp = {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {"tools": TOOLS}
            }
            sys.stdout.write(json.dumps(resp, ensure_ascii=False) + "\n")
            sys.stdout.flush()

        elif method == "tools/call":
            tool_name = params.get("name")
            args = params.get("arguments", {})

            if tool_name == "execute_query":
                db_path = args.get("db_path", "")
                query = args.get("query", "")
                data = execute_query(db_path, query)
                resp = {
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "result": {
                        "content": [{"type": "text", "text": json.dumps(data, ensure_ascii=False, indent=2)}]
                    }
                }
            elif tool_name == "list_tables":
                db_path = args.get("db_path", "")
                data = list_tables(db_path)
                resp = {
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "result": {
                        "content": [{"type": "text", "text": json.dumps(data, ensure_ascii=False, indent=2)}]
                    }
                }
            else:
                resp = {
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "error": {"code": -32601, "message": f"Неизвестный инструмент: {tool_name}"}
                }
            sys.stdout.write(json.dumps(resp, ensure_ascii=False) + "\n")
            sys.stdout.flush()

if __name__ == "__main__":
    main()
