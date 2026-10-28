import sys
import json
import os
import platform
import shutil
import subprocess

# Ensure UTF-8 stdio
if sys.platform == "win32":
    try:
        sys.stdin.reconfigure(encoding='utf-8')
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

def get_system_specs():
    specs = {
        "os": f"{platform.system()} {platform.release()} ({platform.version()})",
        "machine": platform.machine(),
        "processor": platform.processor(),
        "python_version": platform.python_version(),
        "cpu_count": os.cpu_count(),
    }
    # Disk space
    try:
        total, used, free = shutil.disk_usage("C:\\")
        specs["disk_c_total_gb"] = round(total / (1024**3), 1)
        specs["disk_c_free_gb"] = round(free / (1024**3), 1)
    except Exception:
        pass

    # RAM (Windows PowerShell)
    try:
        res = subprocess.run(
            ["powershell", "-NoProfile", "-Command", "(Get-CimInstance Win32_OperatingSystem).TotalVisibleMemorySize, (Get-CimInstance Win32_OperatingSystem).FreePhysicalMemory"],
            capture_output=True, text=True, timeout=5
        )
        lines = [line.strip() for line in res.stdout.strip().split() if line.strip().isdigit()]
        if len(lines) >= 2:
            total_kb, free_kb = int(lines[0]), int(lines[1])
            specs["ram_total_gb"] = round(total_kb / (1024**2), 2)
            specs["ram_free_gb"] = round(free_kb / (1024**2), 2)
    except Exception:
        pass

    return specs

def get_running_processes(limit=15):
    try:
        res = subprocess.run(
            ["powershell", "-NoProfile", "-Command", f"Get-Process | Sort-Object CPU -Descending | Select-Object -First {limit} Id, ProcessName, @{{Name='CPU_Sec';Expression={{[math]::Round($_.CPU, 1)}}}}, @{{Name='RAM_MB';Expression={{[math]::Round($_.WorkingSet64/1MB, 1)}}}} | ConvertTo-Json"],
            capture_output=True, text=True, timeout=8
        )
        return json.loads(res.stdout)
    except Exception as e:
        return {"error": str(e)}

TOOLS = [
    {
        "name": "get_system_specs",
        "description": "Возвращает информацию об ОС, процессоре, объеме оперативной памяти и свободном месте на диске.",
        "inputSchema": {
            "type": "object",
            "properties": {},
            "required": []
        }
    },
    {
        "name": "get_running_processes",
        "description": "Возвращает список самых активных процессов Windows по потреблению CPU и памяти RAM.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "limit": {
                    "type": "integer",
                    "description": "Количество процессов (по умолчанию 15)"
                }
            },
            "required": []
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
                    "serverInfo": {"name": "system-info-mcp", "version": "1.0.0"}
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

            if tool_name == "get_system_specs":
                data = get_system_specs()
                resp = {
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "result": {
                        "content": [{"type": "text", "text": json.dumps(data, ensure_ascii=False, indent=2)}]
                    }
                }
            elif tool_name == "get_running_processes":
                limit = args.get("limit", 15)
                data = get_running_processes(limit)
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
