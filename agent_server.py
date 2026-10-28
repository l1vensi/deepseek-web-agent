import json



import os



import re



import sys



import time



import shutil



import zipfile



import subprocess



import threading



import tkinter as tk



from tkinter import messagebox



from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler



from pathlib import Path



from datetime import datetime



import urllib.request



import urllib.parse



import tempfile



import winsound



import send2trash







# Force UTF-8 for Windows console (prevents cp1251 UnicodeEncodeError on emojis)



if sys.platform == "win32":



    try:



        sys.stdout.reconfigure(encoding='utf-8', errors='replace')



        sys.stderr.reconfigure(encoding='utf-8', errors='replace')



    except Exception:



        pass







PORT = 4050



def setup_auto_proxy():

    """Dynamically detects active Windows system proxy (e.g. 127.0.0.1:10809) if running, routes Python traffic."""

    try:

        import winreg, socket, os

        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Internet Settings") as key:

            enabled, _ = winreg.QueryValueEx(key, "ProxyEnable")

            if enabled:

                proxy_str, _ = winreg.QueryValueEx(key, "ProxyServer")

                if not proxy_str.startswith("http"):

                    proxy_str = f"http://{proxy_str}"

                host_port = proxy_str.replace("http://", "").replace("https://", "").split(":")

                host = host_port[0]

                port = int(host_port[1]) if len(host_port) > 1 else 10809

                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:

                    s.settimeout(0.4)

                    if s.connect_ex((host, port)) == 0:

                        os.environ["HTTP_PROXY"] = proxy_str

                        os.environ["HTTPS_PROXY"] = proxy_str

                        os.environ["NO_PROXY"] = "localhost,127.0.0.1,commons.wikimedia.org,upload.wikimedia.org,wikipedia.org"

                        return proxy_str

    except Exception:

        pass

    os.environ.pop("HTTP_PROXY", None)

    os.environ.pop("HTTPS_PROXY", None)

    return None



active_proxy = setup_auto_proxy()

if active_proxy:

    print(f"🛡️ Автоматически подключен системный VPN-прокси: {active_proxy}")









def get_user_desktop() -> Path:



    """Dynamically finds the real active Desktop path on any Windows PC (OneDrive, Russian/English)."""



    if sys.platform == "win32":



        try:



            import winreg



            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Explorer\User Shell Folders") as key:



                val, _ = winreg.QueryValueEx(key, "Desktop")



                resolved = Path(os.path.expandvars(val))



                if resolved.exists():



                    return resolved



        except Exception:



            pass







    home = Path.home()



    for candidate in [



        home / "OneDrive" / "Рабочий стол",



        home / "OneDrive" / "Desktop",



        home / "Рабочий стол",



        home / "Desktop",



    ]:



        if candidate.exists():



            return candidate







    return home / "Desktop"







DEFAULT_BASE_DIR = get_user_desktop()







def get_default_browser() -> str:



    """Finds the user's active modern browser (Yandex, Chrome, Edge, Firefox) instead of dead Internet Explorer."""



    if sys.platform == "win32":



        try:



            import winreg



            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\Shell\Associations\UrlAssociations\http\UserChoice") as k:



                prog_id, _ = winreg.QueryValueEx(k, "ProgId")



            with winreg.OpenKey(winreg.HKEY_CLASSES_ROOT, rf"{prog_id}\shell\open\command") as cmd_k:



                raw_cmd, _ = winreg.QueryValueEx(cmd_k, "")



                parts = raw_cmd.split('"')



                if len(parts) >= 2 and Path(parts[1]).exists():



                    return parts[1]



        except Exception:



            pass



        for cand in [



            r"C:\Program Files (x86)\Yandex\YandexBrowser\Application\browser.exe",



            r"C:\Program Files\Google\Chrome\Application\chrome.exe",



            r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",



            r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",



        ]:



            if Path(cand).exists():



                return cand



    return ""











# Backup directory for Undo functionality



BACKUPS_DIR = Path(__file__).resolve().parent / ".agent_backups"



# ==============================================================================
# НАСТРОЙКИ СИСТЕМЫ БЭКАПОВ (BACKUP RETENTION & CONFIGURATION)
# ==============================================================================
BACKUP_CONFIG_FILE = Path(__file__).resolve().parent / "backup_config.json"

def get_backup_config():
    """Считывает настройки бэкапов из backup_config.json в реальном времени."""
    default_cfg = {"backup_enabled": True, "retention_days": 7, "max_backup_files": 100}
    if not BACKUP_CONFIG_FILE.exists():
        try:
            with open(BACKUP_CONFIG_FILE, "w", encoding="utf-8") as f:
                json.dump(default_cfg, f, indent=4, ensure_ascii=False)
        except Exception:
            pass
        return default_cfg
    try:
        with open(BACKUP_CONFIG_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            return {
                "backup_enabled": bool(data.get("backup_enabled", True)),
                "retention_days": int(data.get("retention_days", 7)),
                "max_backup_files": int(data.get("max_backup_files", 100))
            }
    except Exception:
        return default_cfg

def cleanup_old_backups():
    """Автоматически удаляет устаревшие бэкапы согласно настройкам backup_config.json."""
    if not BACKUPS_DIR.exists():
        return
    try:
        cfg = get_backup_config()
        if not cfg["backup_enabled"]:
            return
            
        now = time.time()
        files = [f for f in BACKUPS_DIR.iterdir() if f.is_file() and f.name != "trash_index.json"]
        
        # 1. Удаление файлов старше retention_days (если задано > 0)
        retention_days = cfg["retention_days"]
        if retention_days > 0:
            cutoff = now - (retention_days * 86400)
            for f in files:
                try:
                    if f.stat().st_mtime < cutoff:
                        f.unlink(missing_ok=True)
                except Exception:
                    pass
                    
        # 2. Ограничение по общему количеству (FIFO)
        max_files = cfg["max_backup_files"]
        remaining = sorted([f for f in BACKUPS_DIR.iterdir() if f.is_file() and f.name != "trash_index.json"], key=lambda x: x.stat().st_mtime)
        if len(remaining) > max_files:
            for old_f in remaining[:-max_files]:
                try:
                    old_f.unlink(missing_ok=True)
                except Exception:
                    pass
    except Exception as e:
        print(f"⚠️ Ошибка автоочистки бэкапов: {e}")

BACKUP_HISTORY = []







def ask_user_confirmation(title: str, text: str) -> bool:



    """Shows a native topmost Windows popup asking for user permission."""



    root = tk.Tk()



    root.withdraw()



    root.attributes("-topmost", True)



    confirmed = messagebox.askyesno(title, text, parent=root)



    root.destroy()



    return confirmed







def resolve_path(target_path_str: str) -> Path:



    """Resolves relative paths to the user's Desktop or handles absolute paths."""



    p = Path(target_path_str.strip().replace("\\", "/"))



    if p.is_absolute():



        return p



    parts = p.parts



    if parts and parts[0].lower() in ["desktop", "рабочий стол"]:



        return DEFAULT_BASE_DIR.joinpath(*parts[1:])



    return DEFAULT_BASE_DIR.joinpath(*parts)







TRASH_INDEX_FILE = BACKUPS_DIR / "trash_index.json"







def create_backup(target_path: Path):
    """Creates a timestamped backup before modifying/deleting a file or folder for UNDO / RESTORE."""
    cfg = get_backup_config()
    if not cfg["backup_enabled"]:
        return None
    cleanup_old_backups()



    if not target_path.exists():



        return None



    try:



        BACKUPS_DIR.mkdir(parents=True, exist_ok=True)



        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")



        is_dir = target_path.is_dir()



        if is_dir:



            backup_name = f"{target_path.name}_{timestamp}.dirbak"



            backup_path = BACKUPS_DIR / backup_name



            shutil.copytree(target_path, backup_path)



        else:



            backup_name = f"{target_path.stem}_{timestamp}{target_path.suffix}.bak"



            backup_path = BACKUPS_DIR / backup_name



            shutil.copy2(target_path, backup_path)







        record = {



            "name": target_path.name,



            "original_path": str(target_path),



            "backup_path": str(backup_path),



            "is_dir": is_dir,



            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")



        }



        BACKUP_HISTORY.append(record)







        # Update persistent trash index



        trash_list = []



        if TRASH_INDEX_FILE.exists():



            try:



                with open(TRASH_INDEX_FILE, "r", encoding="utf-8") as f:



                    trash_list = json.load(f)



            except Exception:



                trash_list = []



        trash_list.append(record)



        trash_list = trash_list[-50:]



        with open(TRASH_INDEX_FILE, "w", encoding="utf-8") as f:



            json.dump(trash_list, f, ensure_ascii=False, indent=2)







        print(f"💾 Создан бэкап: {backup_name}")



        return backup_path



    except Exception as e:



        print(f"⚠️ Не удалось создать бэкап: {e}")



        return None







def get_windows_system_recycle_bin_items(limit: int = 25):



    """Fetches real items from Windows System Recycle Bin via Shell COM."""



    ps_code = f"""



    [Console]::OutputEncoding = [System.Text.Encoding]::UTF8



    $shell = New-Object -ComObject Shell.Application



    $bin = $shell.Namespace(10)



    $items = $bin.Items()



    $limit = [Math]::Min({limit}, $items.Count)



    for ($i = 0; $i -lt $limit; $i++) {{



        $item = $items.Item($i)



        $orig = $bin.GetDetailsOf($item, 1)



        $date = $bin.GetDetailsOf($item, 2)



        Write-Output "ITEM|$($item.Name)|$orig|$date"



    }}



    """



    tmp = Path(tempfile.gettempdir()) / "read_real_bin.ps1"



    items = []



    try:



        tmp.write_text(ps_code, encoding="utf-8")



        res = subprocess.run(



            ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(tmp)],



            capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=7



        )



        for line in res.stdout.splitlines():



            if line.startswith("ITEM|"):



                parts = line.split("|")



                if len(parts) >= 4:



                    name = parts[1].strip()



                    orig = parts[2].strip()



                    date_del = parts[3].strip().replace("\u200e", "").replace("\u200f", "").strip()



                    items.append({



                        "name": name,



                        "original_path": orig,



                        "timestamp": date_del,



                        "source": "windows_system"



                    })



    except Exception as e:



        print(f"⚠️ Чтение системной корзины Windows: {e}")



    finally:



        if tmp.exists():



            try: tmp.unlink()



            except Exception: pass



    return items







def restore_windows_system_recycle_bin_item(name_filter: str):



    """Restores an item from the real Windows Recycle Bin using the native Shell 'Restore' verb."""



    clean_target = name_filter.strip().replace("'", "''")



    ps_code = f"""



    [Console]::OutputEncoding = [System.Text.Encoding]::UTF8



    $shell = New-Object -ComObject Shell.Application



    $bin = $shell.Namespace(10)



    $found = $false



    foreach ($item in $bin.Items()) {{



        if ("{clean_target}" -eq "" -or $item.Name -like "*{clean_target}*" -or "{clean_target}" -like ("*" + $item.Name + "*")) {{



            foreach ($v in $item.Verbs()) {{



                if ($v.Name -match 'восстанов|restore') {{



                    $v.DoIt()



                    Write-Output "SUCCESS|$($item.Name)"



                    $found = $true



                    break



                }}



            }}



            if ($found) {{ break }}



        }}



    }}



    """



    tmp = Path(tempfile.gettempdir()) / "restore_real_bin.ps1"



    try:



        tmp.write_text(ps_code, encoding="utf-8")



        res = subprocess.run(



            ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(tmp)],



            capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=8



        )



        for line in res.stdout.splitlines():



            if line.startswith("SUCCESS|"):



                restored_name = line.split("|", 1)[1].strip()



                return {"status": "success", "message": f"Файл/папка '{restored_name}' успешно восстановлен(а) из системной Корзины Windows!"}



    except Exception as e:



        print(f"⚠️ Ошибка восстановления из системной Корзины: {e}")



    finally:



        if tmp.exists():



            try: tmp.unlink()



            except Exception: pass



    return None







def restore_from_trash(path_filter: str = ""):



    """Restores deleted file or folder: first tries real Windows Recycle Bin, then falls back to agent backups."""



    # 1. Try Windows System Recycle Bin



    clean_target = Path(path_filter).name if path_filter else ""



    sys_res = restore_windows_system_recycle_bin_item(clean_target)



    if sys_res:



        return sys_res







    # 2. Fallback to .agent_backups / trash_index.json



    trash_list = []



    if TRASH_INDEX_FILE.exists():



        try:



            with open(TRASH_INDEX_FILE, "r", encoding="utf-8") as f:



                trash_list = json.load(f)



        except Exception:



            trash_list = []







    if not trash_list and not BACKUP_HISTORY:



        return {"status": "error", "message": "Объект не найден ни в системной Корзине Windows, ни в бэкапах"}







    target_entry = None



    target_idx = -1



    clean_filter = path_filter.strip().replace("\\", "/").lower() if path_filter else ""







    if clean_filter:



        for idx in range(len(trash_list) - 1, -1, -1):



            entry = trash_list[idx]



            orig = entry.get("original_path", "").replace("\\", "/").lower()



            name = entry.get("name", "").lower()



            if clean_filter in orig or clean_filter in name or clean_filter.endswith(name):



                target_entry = entry



                target_idx = idx



                break



    else:



        if trash_list:



            target_entry = trash_list[-1]



            target_idx = len(trash_list) - 1







    if not target_entry and BACKUP_HISTORY:



        target_entry = BACKUP_HISTORY[-1]







    if not target_entry:



        return {"status": "error", "message": f"Объект '{path_filter}' не найден среди удаленных"}







    orig_path = Path(target_entry["original_path"])



    bak_path = Path(target_entry["backup_path"])



    is_dir = target_entry.get("is_dir", False)







    if not bak_path.exists():



        return {"status": "error", "message": f"Файл резервной копии не найден на диске: {bak_path.name}"}







    try:



        orig_path.parent.mkdir(parents=True, exist_ok=True)



        if is_dir:



            if orig_path.exists():



                shutil.rmtree(orig_path)



            shutil.copytree(bak_path, orig_path)



        else:



            shutil.copy2(bak_path, orig_path)







        if 0 <= target_idx < len(trash_list):



            trash_list.pop(target_idx)



            with open(TRASH_INDEX_FILE, "w", encoding="utf-8") as f:



                json.dump(trash_list, f, ensure_ascii=False, indent=2)







        item_str = "Папка" if is_dir else "Файл"



        print(f"♻️ Восстановлен из бэкапа: {orig_path}")



        return {



            "status": "success",



            "message": f"{item_str} {orig_path.name} успешно восстановлен(а) из резервной копии!",



            "path": str(orig_path)



        }



    except Exception as ex:



        return {"status": "error", "message": f"Ошибка восстановления: {str(ex)}"}







def list_trash_entries():



    """Lists real items from Windows System Recycle Bin combined with agent backups."""



    sys_items = get_windows_system_recycle_bin_items(limit=20)



    



    trash_list = []



    if TRASH_INDEX_FILE.exists():



        try:



            with open(TRASH_INDEX_FILE, "r", encoding="utf-8") as f:



                trash_list = json.load(f)



        except Exception:



            trash_list = []







    lines = []



    if sys_items:



        lines.append(f"🗑️ Системная Корзина Windows (настоящие файлы на ПК, доступно: {len(sys_items)}):")



        for i, item in enumerate(sys_items, 1):



            name = item.get("name", "")



            orig = item.get("original_path", "")



            time_str = item.get("timestamp", "")



            orig_disp = f" -> {orig}" if orig else ""



            lines.append(f"  {i}. [Windows Корзина] {name} ({time_str}){orig_disp}")







    if trash_list:



        lines.append("\n💾 Резервные копии агента (.agent_backups):")



        for i, item in enumerate(reversed(trash_list[-15:]), 1):



            type_badge = "[ПАПКА]" if item.get("is_dir") else "[ФАЙЛ]"



            time_str = item.get("timestamp", "")



            name = item.get("name", "")



            orig = item.get("original_path", "")



            lines.append(f"  {i}. {type_badge} {name} (Удален: {time_str}) -> {orig}")







    if not lines:



        return "Корзина полностью пуста (ни в системной Корзине Windows, ни в бэкапах ничего нет)."







    return "\n".join(lines)







def download_github_folder(url: str, target_dir: Path) -> int:



    """Downloads a folder or entire repository from GitHub (via API or ZIP fallback)."""



    target_dir.mkdir(parents=True, exist_ok=True)



    headers = {



        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',



        'Accept': 'application/vnd.github.v3+json'



    }



    



    # Check if direct zip url



    if url.lower().endswith('.zip'):



        temp_zip = target_dir / "_temp_folder.zip"



        req = urllib.request.Request(url, headers={'User-Agent': headers['User-Agent']})



        with urllib.request.urlopen(req, timeout=30) as f_resp, open(temp_zip, 'wb') as out_f:



            shutil.copyfileobj(f_resp, out_f)



        with zipfile.ZipFile(temp_zip, 'r') as z:



            z.extractall(target_dir)



        if temp_zip.exists():



            temp_zip.unlink()



        return len(list(target_dir.rglob('*')))







    # Match github.com/owner/repo/tree/branch/path or github.com/owner/repo



    m = re.match(r'https?://github\.com/([^/]+)/([^/]+)(?:/tree/([^/]+)/(.*))?', url.rstrip('/'))



    if not m:



        raise ValueError(f"Некорректная ссылка на GitHub: {url}")



    owner, repo, branch, subpath = m.group(1), m.group(2), m.group(3) or "main", m.group(4) or ""



    



    # Try GitHub API first



    api_url = f"https://api.github.com/repos/{owner}/{repo}/contents/{subpath}?ref={branch}"



    try:



        req = urllib.request.Request(api_url, headers=headers)



        with urllib.request.urlopen(req, timeout=15) as resp:



            items = json.loads(resp.read().decode('utf-8'))



        



        file_count = 0



        if isinstance(items, list):



            for item in items:



                if item.get("type") == "file" and item.get("download_url"):



                    f_path = target_dir / item["name"]



                    dl_req = urllib.request.Request(item["download_url"], headers={'User-Agent': headers['User-Agent']})



                    with urllib.request.urlopen(dl_req, timeout=20) as f_resp, open(f_path, 'wb') as out_f:



                        shutil.copyfileobj(f_resp, out_f)



                    file_count += 1



                elif item.get("type") == "dir":



                    file_count += download_github_folder(item.get("html_url", ""), target_dir / item["name"])



            return file_count



    except Exception as e:



        # Fallback: download zip archive of repo and extract subfolder



        print(f"⚠️ GitHub API ({e}), скачиваю через ZIP архива репозитория...")



        zip_url = f"https://github.com/{owner}/{repo}/archive/refs/heads/{branch}.zip"



        temp_zip = target_dir / "_temp_repo.zip"



        dl_req = urllib.request.Request(zip_url, headers={'User-Agent': headers['User-Agent']})



        with urllib.request.urlopen(dl_req, timeout=30) as f_resp, open(temp_zip, 'wb') as out_f:



            shutil.copyfileobj(f_resp, out_f)



        



        extracted_count = 0



        with zipfile.ZipFile(temp_zip, 'r') as z:



            prefix = f"{repo}-{branch}/{subpath}".rstrip('/') + '/'



            for member in z.namelist():



                if subpath:



                    if member.startswith(prefix) and not member.endswith('/'):



                        rel_name = member[len(prefix):]



                        dest = target_dir / rel_name



                        dest.parent.mkdir(parents=True, exist_ok=True)



                        with z.open(member) as src, open(dest, 'wb') as dst:



                            shutil.copyfileobj(src, dst)



                        extracted_count += 1



                else:



                    if not member.endswith('/'):



                        rel_parts = Path(member).parts[1:]



                        if rel_parts:



                            dest = target_dir.joinpath(*rel_parts)



                            dest.parent.mkdir(parents=True, exist_ok=True)



                            with z.open(member) as src, open(dest, 'wb') as dst:



                                shutil.copyfileobj(src, dst)



                            extracted_count += 1



        if temp_zip.exists():



            temp_zip.unlink()



        return extracted_count







class McpClientManager:



    """Manages MCP (Model Context Protocol) JSON-RPC 2.0 servers over stdio."""



    def __init__(self, config_path: Path):



        self.config_path = config_path



        self.processes = {}



        self.request_id = 0







    def _next_id(self):



        self.request_id += 1



        return self.request_id







    def load_config(self):



        if not self.config_path.exists():



            return {}



        try:



            with open(self.config_path, "r", encoding="utf-8") as f:



                return json.load(f).get("mcpServers", {})



        except Exception as e:



            print(f"⚠️ Ошибка чтения mcp_config.json: {e}")



            return {}







    def get_server_process(self, server_name: str):



        if server_name in self.processes:



            p = self.processes[server_name]



            if p.poll() is None:



                return p



            else:



                del self.processes[server_name]







        config = self.load_config()



        if server_name not in config:



            return None







        srv_info = config[server_name]



        cmd = srv_info.get("command")



        args = srv_info.get("args", [])



        full_cmd = [cmd] + args







        script_dir = Path(__file__).resolve().parent



        resolved_cmd = []



        for i, part in enumerate(full_cmd):



            if i > 0 and (script_dir / part).exists():



                resolved_cmd.append(str(script_dir / part))



            else:



                resolved_cmd.append(part)







        try:



            p = subprocess.Popen(



                resolved_cmd,



                stdin=subprocess.PIPE,



                stdout=subprocess.PIPE,



                stderr=subprocess.PIPE,



                text=True,



                encoding='utf-8',



                cwd=str(script_dir),



                bufsize=1



            )



            # JSON-RPC 2.0 initialization handshake



            req_init = {



                "jsonrpc": "2.0",



                "id": self._next_id(),



                "method": "initialize",



                "params": {



                    "protocolVersion": "2024-11-05",



                    "capabilities": {},



                    "clientInfo": {"name": "deepseek-agent-pro", "version": "1.0"}



                }



            }



            p.stdin.write(json.dumps(req_init) + "\n")



            p.stdin.flush()



            p.stdout.readline()







            req_notify = {"jsonrpc": "2.0", "method": "notifications/initialized", "params": {}}



            p.stdin.write(json.dumps(req_notify) + "\n")



            p.stdin.flush()







            self.processes[server_name] = p



            print(f"🔌 MCP сервер '{server_name}' запущен и готов к работе!")



            return p



        except Exception as ex:



            print(f"❌ Не удалось запустить MCP сервер '{server_name}': {ex}")



            return None







    list_tools = lambda self: self.list_all_tools()







    def list_all_tools(self):



        config = self.load_config()



        if not config:



            return "Файл mcp_config.json пуст или не найден. Добавьте MCP серверы в mcp_config.json."







        all_tools_summary = []



        for server_name in config:



            p = self.get_server_process(server_name)



            if not p:



                all_tools_summary.append(f"❌ Сервер [{server_name}]: ошибка запуска.")



                continue







            req = {"jsonrpc": "2.0", "id": self._next_id(), "method": "tools/list", "params": {}}



            try:



                p.stdin.write(json.dumps(req) + "\n")



                p.stdin.flush()



                resp_line = p.stdout.readline()



                data = json.loads(resp_line)



                tools = data.get("result", {}).get("tools", [])



                all_tools_summary.append(f"📦 MCP Сервер [{server_name}]:")



                for t in tools:



                    all_tools_summary.append(f"  • {t['name']}: {t.get('description', '')}")



                    if "inputSchema" in t and "properties" in t["inputSchema"]:



                        props = t["inputSchema"]["properties"]



                        prop_str = ", ".join(f"{k}: {v.get('type')}" for k, v in props.items())



                        all_tools_summary.append(f"    Параметры: {{{prop_str}}}")



            except Exception as e:



                all_tools_summary.append(f"  ⚠️ Ошибка опроса '{server_name}': {e}")







        return "\n".join(all_tools_summary)







    def call_tool(self, server_name: str, tool_name: str, arguments: dict):



        p = self.get_server_process(server_name)



        if not p:



            return {"status": "error", "message": f"Не удалось подключиться к MCP серверу '{server_name}'"}







        req = {



            "jsonrpc": "2.0",



            "id": self._next_id(),



            "method": "tools/call",



            "params": {



                "name": tool_name,



                "arguments": arguments



            }



        }



        try:



            p.stdin.write(json.dumps(req) + "\n")



            p.stdin.flush()



            resp_line = p.stdout.readline()



            data = json.loads(resp_line)



            if "error" in data:



                return {"status": "error", "message": data["error"].get("message", "MCP Tool Error")}







            content_list = data.get("result", {}).get("content", [])



            output_text = "\n".join(item.get("text", "") for item in content_list if item.get("type") == "text")



            return {"status": "success", "content": output_text, "message": f"MCP [{server_name} -> {tool_name}] выполнен"}



        except Exception as e:



            return {"status": "error", "message": f"Ошибка вызова MCP инструмента: {e}"}







mcp_mgr = McpClientManager(Path(__file__).resolve().parent / "mcp_config.json")







def ensure_tokens_file_exists():
    """Automatically creates my_tokens.txt from my_tokens.example.txt on first launch."""
    base_dir = Path(__file__).resolve().parent
    tokens_path = base_dir / "my_tokens.txt"
    example_path = base_dir / "my_tokens.example.txt"
    if not tokens_path.exists() and example_path.exists():
        try:
            import shutil
            shutil.copy2(str(example_path), str(tokens_path))
            print("?? [Tokens] ?????? ???? my_tokens.txt ?? ???????.")
        except Exception:
            pass

def get_custom_image_config():
    ensure_tokens_file_exists()
    """Reads custom AI server URL, Key and Model from my_tokens.txt if provided."""
    tokens = {}
    base_dir = Path(__file__).resolve().parent
    paths = [base_dir / "my_tokens.txt", Path.cwd() / "my_tokens.txt"]
    for p in paths:
        if p.exists():
            try:
                with open(p, "r", encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith("#") and "=" in line:
                            k, v = line.split("=", 1)
                            tokens[k.strip()] = v.strip()
                break
            except Exception:
                pass
    api_url = tokens.get("CUSTOM_IMAGE_API_URL") or tokens.get("IMAGE_API_URL") or tokens.get("IMAGE_SERVER_URL") or ""
    api_key = tokens.get("CUSTOM_IMAGE_API_KEY") or tokens.get("IMAGE_API_KEY") or tokens.get("IMAGE_KEY") or ""
    model_name = tokens.get("CUSTOM_IMAGE_MODEL") or tokens.get("IMAGE_MODEL") or "dall-e-3"
    return api_url.strip(), api_key.strip(), model_name.strip()

class AgentHandler(BaseHTTPRequestHandler):



    def _send_cors_headers(self):



        self.send_header("Access-Control-Allow-Origin", "*")



        self.send_header("Access-Control-Allow-Methods", "POST, GET, OPTIONS")



        self.send_header("Access-Control-Allow-Headers", "Content-Type")







    def _send_json(self, result, status_code=200):



        self.send_response(status_code)



        self._send_cors_headers()



        self.send_header("Content-Type", "application/json; charset=utf-8")



        self.end_headers()



        self.wfile.write(json.dumps(result, ensure_ascii=False).encode("utf-8"))







    def do_OPTIONS(self):



        self.send_response(200)



        self._send_cors_headers()



        self.end_headers()







    def do_GET(self):



        self.send_response(200)



        self._send_cors_headers()



        self.send_header("Content-Type", "application/json; charset=utf-8")



        self.end_headers()



        response = {



            "status": "ok",



            "message": "DeepSeek Agent Bridge Pro (Modes + Download) is running!",



            "workspace": str(DEFAULT_BASE_DIR),



            "backups_count": len(BACKUP_HISTORY)



        }



        self.wfile.write(json.dumps(response, ensure_ascii=False).encode("utf-8"))







    def do_POST(self):



        content_length = int(self.headers.get("Content-Length", 0))



        raw_body = self.rfile.read(content_length).decode("utf-8")



        



        try:



            data = json.loads(raw_body)



        except Exception as e:



            self.send_response(400)



            self._send_cors_headers()



            self.end_headers()



            self.wfile.write(json.dumps({"error": f"Invalid JSON: {str(e)}"}).encode("utf-8"))



            return







        action_type = data.get("action")



        mode = data.get("mode", "standard").lower()  # 'standard', 'safe', 'turbo'



        print(f"\n[ACTION]: {action_type} | [MODE]: {mode.upper()}")







        def should_ask(is_destructive: bool) -> bool:



            if mode == "turbo":



                return False



            if mode == "standard":



                return is_destructive  # only ask for destructive operations



            return True  # safe mode: ask for everything







        # 1. CREATE_FOLDER (Safe action)



        if action_type == "CREATE_FOLDER":



            path_str = data.get("path", "")



            target_path = resolve_path(path_str)



            needs_confirm = should_ask(is_destructive=False)



            



            prompt_msg = f"DeepSeek запрашивает СОЗДАНИЕ ПАПКИ:\n\n📁 Путь: {target_path}\n\nРазрешить создание?"



            



            if not needs_confirm or ask_user_confirmation("Подтверждение: Создать папку", prompt_msg):



                try:



                    target_path.mkdir(parents=True, exist_ok=True)



                    print(f"✅ Создана папка: {target_path}")



                    result = {"status": "success", "message": f"Папка создана: {target_path.name}"}



                except Exception as ex:



                    result = {"status": "error", "message": str(ex)}



            else:



                result = {"status": "rejected", "message": "Действие отклонено пользователем"}







        # 2. WRITE_FILE (Destructive only if overwriting existing file)



        elif action_type == "WRITE_FILE":



            path_str = data.get("path", "")



            code_content = data.get("content", "")



            target_path = resolve_path(path_str)



            file_exists = target_path.exists()



            



            # Clean possible markdown block wrappers and smushed button labels



            clean_content = code_content.strip()



            clean_content = re.sub(r"^```[a-zA-Z0-9_-]*\s*\n", "", clean_content)



            clean_content = re.sub(r"\n```\s*$", "", clean_content)







            lines = clean_content.splitlines()



            artifacts = ["copy", "download", "run", "preview", "копировать", "скачать", "запустить", "просмотр", "python", "py", "python3", "html", "javascript", "js", "css", "json", "bash", "sh", "```"]



            while lines and lines[0].strip().lower() in artifacts:



                lines.pop(0)



            if lines:



                lines[0] = re.sub(r'^(?:python|copy|download|run|preview|копировать|скачать|запустить|просмотр|py)+', '', lines[0], flags=re.IGNORECASE).lstrip()



            while lines and lines[-1].strip() in ["```", "```python"]:



                lines.pop(-1)



            clean_content = "\n".join(lines)







            lines_count = len(clean_content.splitlines())



            



            # Anti-flattening guard: detect if browser/markdown smushed multi-line code into a single line



            if len(clean_content) > 150 and lines_count == 1 and target_path.suffix.lower() in ['.py', '.js', '.html', '.css', '.json']:



                err_msg = f"Отказ записи: код файла {target_path.name} склеился в одну строку ({len(clean_content)} симв.). Оберни код в тройные кавычки ```!"



                print(f"⚠️ {err_msg}")



                result = {"status": "error", "message": err_msg}



                self._send_json(result)



                return







            preview = clean_content[:200] + ("..." if len(clean_content) > 200 else "")



            



            needs_confirm = should_ask(is_destructive=False)



            action_title = "ПЕРЕЗАПИСЬ файла" if file_exists else "Создание нового файла"



            prompt_msg = (



                f"DeepSeek запрашивает {action_title}:\n\n"



                f"📄 Файл: {target_path}\n"



                f"📊 Строк: {lines_count}\n\n"



                f"Превью:\n{preview}\n\n"



                f"Разрешить запись?"



            )



            



            if not needs_confirm or ask_user_confirmation(f"Подтверждение: {action_title}", prompt_msg):



                try:



                    target_path.parent.mkdir(parents=True, exist_ok=True)



                    create_backup(target_path)



                    with open(target_path, "w", encoding="utf-8") as f:



                        f.write(clean_content)



                    print(f"✅ Записан файл: {target_path}")



                    result = {"status": "success", "message": f"Файл сохранен: {target_path.name}"}



                except Exception as ex:



                    result = {"status": "error", "message": str(ex)}



            else:



                result = {"status": "rejected", "message": "Действие отклонено пользователем"}







        # 3. DOWNLOAD_FILE (Download from internet/github)



        elif action_type == "DOWNLOAD_FILE":



            url = data.get("url", "").strip()



            path_str = data.get("path", "").strip()



            target_path = resolve_path(path_str)



            needs_confirm = should_ask(is_destructive=False)



            



            # Auto-heal deprecated or blocked Wikimedia thumb domains



            if "thumb.wikimedia.org" in url:



                url = url.replace("thumb.wikimedia.org", "upload.wikimedia.org")



            



            prompt_msg = (



                f"DeepSeek запрашивает СКАЧИВАНИЕ ИЗ ИНТЕРНЕТА:\n\n"



                f"🌐 URL: {url}\n"



                f"📁 Сохранить в: {target_path}\n\n"



                f"Разрешить скачивание?"



            )



            



            if not needs_confirm or ask_user_confirmation("Подтверждение: Скачивание файла", prompt_msg):



                try:



                    target_path.parent.mkdir(parents=True, exist_ok=True)



                    print(f"🌐 Скачивание {url} -> {target_path} ...")



                    browser_headers = {



                        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36',



                        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',



                        'Accept-Language': 'ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7',



                        'Sec-Ch-Ua': '"Chromium";v="129", "Not=A?Brand";v="24", "Google Chrome";v="129"',



                        'Sec-Ch-Ua-Mobile': '?0',



                        'Sec-Ch-Ua-Platform': '"Windows"',



                        'Sec-Fetch-Dest': 'document',



                        'Sec-Fetch-Mode': 'navigate',



                        'Sec-Fetch-Site': 'none',



                        'Sec-Fetch-User': '?1',



                        'Upgrade-Insecure-Requests': '1'



                    }



                    try:



                        import requests



                        session = requests.Session()



                        resp = session.get(url, headers=browser_headers, allow_redirects=True, timeout=25)



                        if resp.status_code == 429:



                            print("⏳ Сервер вернул 429 (Too Many Requests), повтор через 3 секунды...")



                            time.sleep(3)



                            resp = session.get(url, headers=browser_headers, allow_redirects=True, timeout=25)



                        resp.raise_for_status()



                        with open(target_path, 'wb') as out_file:



                            out_file.write(resp.content)



                    except ImportError:



                        req = urllib.request.Request(url, headers=browser_headers)



                        try:



                            with urllib.request.urlopen(req, timeout=25) as response, open(target_path, 'wb') as out_file:



                                shutil.copyfileobj(response, out_file)



                        except urllib.error.HTTPError as he:



                            if he.code == 429:



                                time.sleep(3)



                                with urllib.request.urlopen(req, timeout=25) as response, open(target_path, 'wb') as out_file:



                                    shutil.copyfileobj(response, out_file)



                            else:



                                raise



                    size_kb = round(target_path.stat().st_size / 1024, 1)



                    print(f"✅ Успешно скачано: {target_path.name} ({size_kb} KB)")



                    result = {"status": "success", "message": f"Файл скачан: {target_path.name} ({size_kb} KB)"}



                except Exception as ex:



                    print(f"❌ Ошибка скачивания: {ex}")



                    domain = urllib.parse.urlparse(url).netloc.lower()



                    tip = ""



                    if "unsplash" in domain or "picsum" in domain:



                        tip = (



                            f"\n💡 ДИАГНОЗ И ДЕЙСТВИЕ ДЛЯ DEEPSEEK: Домен {domain} заблокирован защитой стока (403/Timeout). "



                            f"СТРОЖАЙШЕ ЗАПРЕЩЕНО повторять ссылки с {domain}! "



                            f"Вызови инструмент MCP search_free_media: <<<ACTION: MCP_CALL | SERVER: web_search | TOOL: search_free_media | ARGS: {{\"query\": \"тема\"}}>>> "



                            f"для получения настоящих проверенных ссылок на фото/видео из Википедии (upload.wikimedia.org) или используй SVG-графику!"



                        )



                    elif "wikimedia" in domain and "thumb." in domain:



                        tip = "\n💡 ДЕЙСТВИЕ ДЛЯ DEEPSEEK: Замени домен thumb.wikimedia.org на upload.wikimedia.org!"



                    else:



                        tip = f"\n💡 ДЕЙСТВИЕ ДЛЯ DEEPSEEK: Ссылка {url} недоступна. Вызови MCP search_free_media или используй векторный SVG!"



                    result = {"status": "error", "message": f"Ошибка скачивания: {str(ex)}{tip}"}



            else:



                result = {"status": "rejected", "message": "Скачивание отклонено пользователем"}







        # 3b. DOWNLOAD_FOLDER (Download folder or repo from GitHub or ZIP)



        elif action_type == "DOWNLOAD_FOLDER":



            url = data.get("url", "").strip()



            path_str = data.get("path", "").strip()



            target_path = resolve_path(path_str)



            needs_confirm = should_ask(is_destructive=False)



            



            prompt_msg = (



                f"DeepSeek запрашивает СКАЧИВАНИЕ ПАПКИ:\n\n"



                f"🌐 URL: {url}\n"



                f"📁 Сохранить в: {target_path}\n\n"



                f"Разрешить скачивание папки?"



            )



            



            if not needs_confirm or ask_user_confirmation("Подтверждение: Скачивание папки", prompt_msg):



                try:



                    target_path.mkdir(parents=True, exist_ok=True)



                    print(f"🌐 Скачивание папки {url} -> {target_path} ...")



                    count = download_github_folder(url, target_path)



                    print(f"✅ Папка успешно скачана: {target_path.name} (файлов: {count})")



                    result = {"status": "success", "message": f"Папка скачана: {target_path.name} ({count} файлов)"}



                except Exception as ex:



                    print(f"❌ Ошибка скачивания папки: {ex}")



                    result = {"status": "error", "message": f"Ошибка скачивания папки: {str(ex)}"}



            else:



                result = {"status": "rejected", "message": "Скачивание папки отклонено пользователем"}







        # 4. REPLACE_TEXT (Destructive)



        elif action_type == "REPLACE_TEXT":



            path_str = data.get("path", "")



            target_str = data.get("target", "")



            replacement_str = data.get("replacement", "")



            target_path = resolve_path(path_str)







            if not target_path.exists():



                result = {"status": "error", "message": f"Файл не найден: {target_path}"}



            else:



                needs_confirm = should_ask(is_destructive=False)



                prompt_msg = (



                    f"Точечная замена в файле:\n{target_path.name}\n\n"



                    f"НАЙТИ:\n{target_str[:120]}\n\n"



                    f"ЗАМЕНИТЬ НА:\n{replacement_str[:120]}\n\n"



                    f"Разрешить замену?"



                )



                if not needs_confirm or ask_user_confirmation("Подтверждение: Точечная замена", prompt_msg):



                    try:



                        with open(target_path, "r", encoding="utf-8", errors="replace") as f:



                            text = f.read()







                        if target_str in text:



                            create_backup(target_path)



                            new_text = text.replace(target_str, replacement_str, 1)



                            with open(target_path, "w", encoding="utf-8") as f:



                                f.write(new_text)



                            print(f"✂️ Выполнена точечная замена в {target_path}")



                            result = {"status": "success", "message": f"Текст заменен в файле {target_path.name}"}



                        else:



                            # Fuzzy whitespace-flexible match: handles indentation / space discrepancies



                            stripped_target = target_str.strip()



                            tokens = [re.escape(tok) for tok in re.split(r'\s+', stripped_target) if tok]



                            matched = False



                            if tokens:



                                fuzzy_pattern = r'\s+'.join(tokens)



                                m = re.search(fuzzy_pattern, text)



                                if m:



                                    create_backup(target_path)



                                    span = m.span()



                                    new_text = text[:span[0]] + replacement_str + text[span[1]:]



                                    with open(target_path, "w", encoding="utf-8") as f:



                                        f.write(new_text)



                                    print(f"✂️ Выполнена умная точечная замена (с авто-подгонкой отступов) в {target_path}")



                                    result = {"status": "success", "message": f"Текст успешно заменен в файле {target_path.name} (с авто-подгонкой отступов)"}



                                    matched = True



                                else:



                                    # Comment typo fallback: e.g. '/* ... /' missing '*'



                                    fixed_target = re.sub(r'/\*([^\n*]+)/\s*$', r'/*\1*/', stripped_target, flags=re.MULTILINE)



                                    if fixed_target != stripped_target:



                                        fix_tokens = [re.escape(tok) for tok in re.split(r'\s+', fixed_target) if tok]



                                        m2 = re.search(r'\s+'.join(fix_tokens), text)



                                        if m2:



                                            create_backup(target_path)



                                            span = m2.span()



                                            new_text = text[:span[0]] + replacement_str + text[span[1]:]



                                            with open(target_path, "w", encoding="utf-8") as f:



                                                f.write(new_text)



                                            print(f"✂️ Выполнена умная точечная замена (с авто-исправлением опечатки в комментарии) в {target_path}")



                                            result = {"status": "success", "message": f"Текст успешно заменен в файле {target_path.name} (с авто-коррекцией опечатки)"}



                                            matched = True







                            if not matched:



                                result = {



                        "status": "error",



                        "message": (



                            "Искомый фрагмент текста не найден в файле. "



                            "\n💡 ДЕЙСТВИЕ ДЛЯ DEEPSEEK: СТРОГО ЗАПРЕЩЕНО угадывать строки! "



                            "Прочитай актуальный файл через READ_FILE или перезапиши его целиком через WRITE_FILE."



                        )



                    }



                    except Exception as ex:



                        result = {"status": "error", "message": str(ex)}



                else:



                    result = {"status": "rejected", "message": "Замена отклонена пользователем"}







        # 5. READ_FILE (Safe)



        elif action_type == "READ_FILE":



            path_str = data.get("path", "")



            target_path = resolve_path(path_str)



            if not target_path.exists():



                result = {"status": "error", "message": f"Файл не найден: {target_path}"}



            else:



                try:



                    with open(target_path, "r", encoding="utf-8", errors="replace") as f:



                        content = f.read()



                    print(f"📖 Прочитан файл: {target_path} ({len(content)} символов)")



                    result = {



                        "status": "success",



                        "content": content,



                        "path": str(target_path),



                        "message": f"Файл прочитан ({len(content)} симв.): {target_path.name}"



                    }



                except Exception as ex:



                    result = {"status": "error", "message": str(ex)}







        # 6. DELETE_FILE / DELETE_FOLDER (Recycle Bin + Persistent Backup)



        elif action_type in ["DELETE_FILE", "DELETE_FOLDER"]:



            path_str = data.get("path", "")



            target_path = resolve_path(path_str)



            if not target_path.exists():



                result = {"status": "error", "message": f"Объект не существует: {target_path}"}



            else:



                is_dir = target_path.is_dir()



                item_label = "ПАПКУ" if is_dir else "ФАЙЛ"



                needs_confirm = should_ask(is_destructive=False)



                prompt_msg = f"УДАЛИТЬ В КОРЗИНУ {item_label}?\n\n🗑️ {target_path}\n\nОбъект будет перемещен в Корзину Windows и сохранен в бэкапах (можно вернуть через RESTORE_FILE)."



                if not needs_confirm or ask_user_confirmation(f"Подтверждение: Удаление ({item_label})", prompt_msg):



                    try:



                        create_backup(target_path)



                        send2trash.send2trash(str(target_path))



                        print(f"🗑️ Отправлен в корзину {item_label}: {target_path}")



                        result = {"status": "success", "message": f"Перемещен(а) в Корзину {item_label}: {target_path.name}"}



                    except Exception as ex:



                        result = {"status": "error", "message": str(ex)}



                else:



                    result = {"status": "rejected", "message": "Удаление отклонено пользователем"}







        # 6b. RESTORE_FILE / RESTORE_TRASH / RESTORE_FOLDER (Restore from Recycle Bin)



        elif action_type in ["RESTORE_FILE", "RESTORE_TRASH", "RESTORE_FOLDER"]:



            path_str = data.get("path", "")



            needs_confirm = should_ask(is_destructive=False)



            prompt_msg = f"ВОССТАНОВИТЬ ИЗ КОРЗИНЫ?\n\n♻️ {path_str or 'Последний удаленный объект'}\n\nРазрешить восстановление?"



            if not needs_confirm or ask_user_confirmation("Подтверждение: Восстановление из корзины", prompt_msg):



                result = restore_from_trash(path_str)



            else:



                result = {"status": "rejected", "message": "Восстановление отклонено пользователем"}







        # 6c. LIST_TRASH (View items in Recycle Bin / Backups)



        elif action_type in ["LIST_TRASH", "TRASH"]:



            summary = list_trash_entries()



            print("🗑️ Запрошен список корзины")



            result = {



                "status": "success",



                "content": summary,



                "message": "Список корзины получен"



            }







        # 7. RENAME / MOVE (Files and Folders)



        elif action_type in ["RENAME", "MOVE", "RENAME_FILE", "RENAME_FOLDER", "MOVE_FILE", "MOVE_FOLDER"]:



            src_str = data.get("from", data.get("src", data.get("path", ""))).strip()



            dst_str = data.get("to", data.get("dst", data.get("new_path", ""))).strip()



            src_path = resolve_path(src_str)



            dst_path = resolve_path(dst_str)



            



            if not src_path.exists():



                result = {"status": "error", "message": f"Исходный объект не найден: {src_path}"}



            else:



                is_dir = src_path.is_dir()



                item_label = "папку" if is_dir else "файл"



                needs_confirm = should_ask(is_destructive=False)



                prompt_msg = f"Переименовать/переместить {item_label}?\n\nИЗ: {src_path}\nВ:  {dst_path}"



                if not needs_confirm or ask_user_confirmation("Подтверждение: Переименование/Перемещение", prompt_msg):



                    try:



                        dst_path.parent.mkdir(parents=True, exist_ok=True)



                        shutil.move(str(src_path), str(dst_path))



                        print(f"📦 Переименован(а) {item_label}: {src_path.name} -> {dst_path.name}")



                        result = {"status": "success", "message": f"{item_label.capitalize()} успешно переименован(а) в {dst_path.name}"}



                    except Exception as ex:



                        result = {"status": "error", "message": str(ex)}



                else:



                    result = {"status": "rejected", "message": "Переименование отклонено пользователем"}







        # 7b. COPY (Files and Folders - Copy & Paste)



        elif action_type in ["COPY", "COPY_FILE", "COPY_FOLDER"]:



            src_str = data.get("from", data.get("src", data.get("path", ""))).strip()



            dst_str = data.get("to", data.get("dst", data.get("new_path", ""))).strip()



            src_path = resolve_path(src_str)



            dst_path = resolve_path(dst_str)



            



            if not src_path.exists():



                result = {"status": "error", "message": f"Исходный объект не найден: {src_path}"}



            else:



                is_dir = src_path.is_dir()



                item_label = "папку" if is_dir else "файл"



                needs_confirm = should_ask(is_destructive=False)



                prompt_msg = f"Копировать {item_label}?\n\nИЗ: {src_path}\nВ:  {dst_path}"



                if not needs_confirm or ask_user_confirmation("Подтверждение: Копирование", prompt_msg):



                    try:



                        dst_path.parent.mkdir(parents=True, exist_ok=True)



                        if is_dir:



                            shutil.copytree(str(src_path), str(dst_path), dirs_exist_ok=True)



                        else:



                            shutil.copy2(str(src_path), str(dst_path))



                        print(f"📋 Скопирован(а) {item_label}: {src_path.name} -> {dst_path.name}")



                        result = {"status": "success", "message": f"{item_label.capitalize()} успешно скопирован(а) в {dst_path.name}"}



                    except Exception as ex:



                        result = {"status": "error", "message": str(ex)}



                else:



                    result = {"status": "rejected", "message": "Копирование отклонено пользователем"}







        # 7c. GENERATE_IMAGE (Free AI Image Generation via Pollinations FLUX/Turbo)



        elif action_type in ["GENERATE_IMAGE", "GEN_IMAGE", "CREATE_IMAGE"]:



            prompt = data.get("prompt", data.get("query", "")).strip()



            dest_str = data.get("path", data.get("dest", "")).strip()



            if not prompt or not dest_str:



                result = {"status": "error", "message": "Не указан prompt (описание) или path (путь сохранения файла)"}



            else:



                dest_path = resolve_path(dest_str)



                needs_confirm = should_ask(is_destructive=False)



                prompt_msg = f"Сгенерировать AI изображение?\n\n🎨 Описание: {prompt}\n📁 Файл: {dest_path}"



                if not needs_confirm or ask_user_confirmation("Подтверждение: Генерация изображения", prompt_msg):



                    try:



                        dest_path.parent.mkdir(parents=True, exist_ok=True)



                        chosen_model = data.get("model", "").strip().lower()



                        valid_models = ["turbo", "flux-realism", "flux", "midjourney", "flux-anime", "dalle"]



                        



                        if chosen_model not in valid_models:



                            # Auto-select best model based on prompt keywords if not explicitly specified



                            p_lower = prompt.lower()



                            if any(k in p_lower for k in ["anime", "manga", "chibi", "kawaii"]):



                                chosen_model = "flux-anime"



                            elif any(k in p_lower for k in ["photo", "realistic", "realism", "portrait", "architecture", "interior", "car"]):



                                chosen_model = "flux-realism"



                            elif any(k in p_lower for k in ["cinematic", "fantasy", "art", "epic", "poster", "wallpaper"]):



                                chosen_model = "midjourney"



                            elif any(k in p_lower for k in ["vector", "icon", "logo", "flat illustration", "cartoon"]):



                                chosen_model = "dalle"



                            else:



                                chosen_model = "turbo"



                                



                        # Auto-enrich prompt with professional photography keywords for crisp 8K detail



                        enhanced_prompt = prompt



                        quality_keywords = ["sharp focus", "photorealistic", "8k", "uhd", "high resolution", "detailed"]



                        if not any(k in prompt.lower() for k in quality_keywords):



                            enhanced_prompt = f"{prompt}, sharp focus, 8k uhd, photorealistic, cinematic lighting, 35mm photography"



                        



                        encoded_prompt = urllib.parse.quote(enhanced_prompt)



                        # Multi-tier resilient fallback:



                        # 1) chosen model + 16:9 widescreen



                        # 2) chosen model default dimensions



                        # 3) fast turbo model



                        # 4) standard fallback



                        # 1:1 Square aspect ratio (1024x1024 / native) - zero distortion

                        candidate_urls = [

                            f"https://image.pollinations.ai/prompt/{encoded_prompt}?model={chosen_model}&width=1024&height=1024&nologo=true",

                            f"https://image.pollinations.ai/prompt/{encoded_prompt}?model={chosen_model}&nologo=true",

                            f"https://image.pollinations.ai/prompt/{encoded_prompt}?model=turbo&width=1024&height=1024&nologo=true",

                            f"https://image.pollinations.ai/prompt/{encoded_prompt}?model=turbo&nologo=true",

                            f"https://image.pollinations.ai/prompt/{encoded_prompt}?nologo=true"

                        ]



                        



                        img_data = None



                        last_err = None



                        # Custom AI Server Gateway (OpenAI / Any Image Generation API)
                        c_url, c_key, c_model = get_custom_image_config()
                        if c_url and 'your_server' not in c_key.lower():
                            try:
                                import base64
                                print(f"?? ??????? ????????? ????? ???????????????? ??????: {c_url}...")
                                post_body = json.dumps({
                                    "prompt": prompt,
                                    "model": c_model or "dall-e-3",
                                    "n": 1,
                                    "size": "1024x1024"
                                }).encode("utf-8")
                                headers = {
                                    "Content-Type": "application/json",
                                    "User-Agent": "DeepSeek-Web-Agent/2.0"
                                }
                                if c_key:
                                    headers["Authorization"] = f"Bearer {c_key}"
                                    headers["x-api-key"] = c_key
                                    headers["x-goog-api-key"] = c_key
                                custom_req = urllib.request.Request(c_url, data=post_body, headers=headers)
                                with urllib.request.urlopen(custom_req, timeout=40) as custom_resp:
                                    resp_json = json.loads(custom_resp.read().decode("utf-8"))
                                    if "data" in resp_json and len(resp_json["data"]) > 0:
                                        first_item = resp_json["data"][0]
                                        if "b64_json" in first_item:
                                            img_data = base64.b64decode(first_item["b64_json"])
                                        elif "url" in first_item:
                                            with urllib.request.urlopen(first_item["url"], timeout=20) as u_resp:
                                                img_data = u_resp.read()
                                if img_data:
                                    print(f"? ??????? ????????????? ????? ???????????????? ?????? ({c_model})!")
                            except Exception as c_err:
                                print(f"?? ?????? ??????? ({c_err}). ??????? ????????? ?????????...")

                        if not img_data:
                            for target_url in candidate_urls:



                                for retry in range(2):



                                    try:



                                        req = urllib.request.Request(target_url, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"})



                                        with urllib.request.urlopen(req, timeout=35) as resp:



                                            img_data = resp.read()



                                            if len(img_data) > 1000:



                                                break



                                    except urllib.error.HTTPError as h_err:



                                        last_err = h_err



                                        body = h_err.read().decode("utf-8", errors="ignore")



                                        if h_err.code == 402 and "Retry after" in body:



                                            try:



                                                wait_sec = int(body.split("Retry after")[1].split("s")[0].strip())



                                                wait_sec = min(max(wait_sec + 2, 3), 46)



                                                print(f"⏳ Pollinations cooldown: ожидание {wait_sec} сек...")



                                                time.sleep(wait_sec)



                                                continue



                                            except Exception:



                                                pass



                                        break



                                    except Exception as u_err:



                                        last_err = u_err



                                        break



                                if img_data:



                                    break



                        



                        if not img_data:



                            raise Exception(f"Не удалось получить изображение от серверов генерации: {last_err}")



                        



                        # Clean watermark cleanly preserving pure 1:1 square proportions (NO stretching!)

                        try:

                            from PIL import Image

                            import io

                            raw_img = Image.open(io.BytesIO(img_data))

                            w, h = raw_img.size

                            trim_bottom = min(36, int(h * 0.05))

                            if abs(w - h) < 60:

                                square_size = min(w, h - trim_bottom)

                                offset_x = (w - square_size) // 2

                                clean_img = raw_img.crop((offset_x, 0, offset_x + square_size, square_size))

                            else:

                                clean_img = raw_img.crop((0, 0, w, h - trim_bottom))

                                                        # Automatic HD Quality Enhancer: unsharp mask (removes blur) + micro-contrast (removes AI fog)

                            try:

                                from PIL import ImageEnhance, ImageFilter

                                clean_img = clean_img.filter(ImageFilter.UnsharpMask(radius=1.5, percent=135, threshold=3))

                                clean_img = ImageEnhance.Contrast(clean_img).enhance(1.06)

                            except Exception:

                                pass

                            clean_img.save(dest_path, "JPEG", quality=95)

                            print(f"✨ Чистое 1:1 квадратное фото [{chosen_model}] ({clean_img.size[0]}x{clean_img.size[1]}) без водяных знаков и растягиваний сохранено: {dest_path.name}")

                        except Exception as p_err:



                            with open(dest_path, "wb") as f:



                                f.write(img_data)



                        



                        size_kb = round(len(img_data) / 1024, 1)



                        print(f"🎨 Сгенерировано фото [{chosen_model}] ({size_kb} KB): {dest_path}")



                        result = {



                            "status": "success",



                            "message": f"Изображение успешно сгенерировано [{chosen_model}] ({size_kb} KB) без водяных знаков и сохранено в {dest_path.name}!",



                            "path": str(dest_path)



                        }



                    except Exception as ex:



                        print(f"❌ Ошибка генерации фото: {ex}")



                        result = {"status": "error", "message": f"Ошибка генерации фото: {str(ex)}"}



                else:



                    result = {"status": "rejected", "message": "Генерация изображения отклонена пользователем"}







        # 8. LIST_DIR (Safe)



        elif action_type in ["LIST_DIR", "TREE"]:



            path_str = data.get("path", "")



            target_dir = resolve_path(path_str) if path_str else DEFAULT_BASE_DIR



            if not target_dir.exists():



                result = {"status": "error", "message": f"Папка не найдена: {target_dir}"}



            else:



                try:



                    entries = []



                    for root_dir, dirs, files in os.walk(target_dir):



                        dirs[:] = [d for d in dirs if not d.startswith(".") and d not in ["__pycache__", "node_modules"]]



                        rel_root = os.path.relpath(root_dir, target_dir)



                        for f in files:



                            if not f.startswith("."):



                                f_path = Path(root_dir) / f



                                size_kb = round(f_path.stat().st_size / 1024, 1)



                                entries.append(f"{rel_root}/{f} ({size_kb} KB)")



                        if len(entries) > 100:



                            break



                    tree_text = "\n".join(entries[:80]) or "[Папка пуста]"



                    print(f"🌲 Дерево папки {target_dir.name}: найдено {len(entries)} файлов")



                    result = {"status": "success", "content": tree_text, "message": f"Найдено файлов: {len(entries)}"}



                except Exception as ex:



                    result = {"status": "error", "message": str(ex)}







        # 9. ZIP_FOLDER / UNZIP



        elif action_type == "ZIP_FOLDER":



            folder_str = data.get("path", "")



            target_folder = resolve_path(folder_str)



            zip_dest = target_folder.parent / f"{target_folder.name}.zip"



            if not target_folder.exists():



                result = {"status": "error", "message": f"Папка не найдена: {target_folder}"}



            else:



                try:



                    shutil.make_archive(str(target_folder.parent / target_folder.name), 'zip', str(target_folder))



                    result = {"status": "success", "message": f"Архив создан: {zip_dest.name}"}



                except Exception as ex:



                    result = {"status": "error", "message": str(ex)}







        elif action_type == "UNZIP":



            zip_str = data.get("path", "")



            target_zip = resolve_path(zip_str)



            extract_to = target_zip.parent / target_zip.stem



            if not target_zip.exists():



                result = {"status": "error", "message": f"Архив не найден: {target_zip}"}



            else:



                try:



                    with zipfile.ZipFile(target_zip, 'r') as zf:



                        zf.extractall(extract_to)



                    result = {"status": "success", "message": f"Распаковано в папку: {extract_to.name}"}



                except Exception as ex:



                    result = {"status": "error", "message": str(ex)}







        # 10. UNDO



        elif action_type == "UNDO":



            if not BACKUP_HISTORY:



                result = {"status": "error", "message": "Нет доступных действий для отката"}



            else:



                last_backup = BACKUP_HISTORY.pop()



                orig_file = Path(last_backup["original_path"])



                bak_file = Path(last_backup["backup_path"])



                prompt_msg = f"ОТКАТИТЬ ДЕЙСТВИЕ?\n\nВосстановить предыдущую версию файла:\n{orig_file.name}?"



                needs_confirm = should_ask(is_destructive=False)



                if not needs_confirm or ask_user_confirmation("Подтверждение: Откат (UNDO)", prompt_msg):



                    try:



                        shutil.copy2(bak_file, orig_file)



                        print(f"⏪ Восстановлен файл: {orig_file.name}")



                        result = {"status": "success", "message": f"Файл {orig_file.name} успешно восстановлен!"}



                    except Exception as ex:



                        result = {"status": "error", "message": str(ex)}



                else:



                    BACKUP_HISTORY.append(last_backup)



                    result = {"status": "rejected", "message": "Откат отменен"}







        # 11. OPEN_FILE (Safe)



        elif action_type == "OPEN_FILE":



            path_str = data.get("path", "")



            target_path = resolve_path(path_str)



            if not target_path.exists():



                result = {"status": "error", "message": f"Файл не существует: {target_path}"}



            else:



                needs_confirm = should_ask(is_destructive=False)



                prompt_msg = f"Открыть файл/приложение?\n\n🚀 {target_path}\n\nРазрешить запуск?"



                if not needs_confirm or ask_user_confirmation("Подтверждение: Запуск программы", prompt_msg):



                    try:



                        if target_path.suffix.lower() in [".html", ".htm"]:



                            real_b = get_default_browser()



                            if real_b:



                                subprocess.Popen([real_b, str(target_path)])



                                b_name = Path(real_b).stem



                                print(f"🌐 Открыт сайт в браузере ({b_name}): {target_path}")



                                result = {"status": "success", "message": f"Сайт открыт в браузере {b_name}: {target_path.name}"}



                            else:



                                os.startfile(str(target_path))



                                print(f"🚀 Запущен файл: {target_path}")



                                result = {"status": "success", "message": f"Файл запущен: {target_path.name}"}



                        else:



                            os.startfile(str(target_path))



                            print(f"🚀 Запущен файл: {target_path}")



                            result = {"status": "success", "message": f"Файл запущен: {target_path.name}"}



                    except Exception as ex:



                        result = {"status": "error", "message": str(ex)}



                else:



                    result = {"status": "rejected", "message": "Запуск отклонен"}







        # 12. RUN_COMMAND (Destructive unless harmless inspector)



        elif action_type == "RUN_COMMAND":



            command = data.get("cmd", "").strip()



            



            desktop_native = str(DEFAULT_BASE_DIR).rstrip("\\/")



            



                        # 1. Normalize existing C:\Users\...\Desktop to active OneDrive desktop (prevents double nesting!)

            normalized_cmd = re.sub(

                r"[A-Za-z]:\\[^\r\n]+?\\Desktop([\\/])",

                lambda m: desktop_native + m.group(1),

                command,

                flags=re.I

            )

            # 2. Quoted Desktop paths: "Desktop/path" -> "C:\Users\...\path"
            pattern_quoted = r'["\']Desktop[/\\]([^"\']+)["\']'
            normalized_cmd = re.sub(
                pattern_quoted,
                lambda m: f'"{desktop_native}\\{m.group(1).replace("/", "\\")}"',
                normalized_cmd
            )

            # 3. Unquoted standalone Desktop paths: Desktop/path -> "C:\Users\...\path"
            pattern_unquoted = r'(?<![A-Za-z0-9_:\\"\'\\])Desktop[/\\]([^"\'><|&;\s]+)'
            normalized_cmd = re.sub(
                pattern_unquoted,
                lambda m: f'"{desktop_native}\\{m.group(1).strip().replace("/", "\\")}"',
                normalized_cmd
            )
            dangerous_patterns = [



                r"\bdel\s+/[fqs]", r"\brmdir\s+/[sq]", r"\bformat\s+[a-z]:",



                r"\bdrop\s+(?:database|table)\b", r"\btruncate\s+table\b",



                r"\bshutdown\b", r"\btaskkill\b", r"remove-item\s+-[^\n]*recurse"



            ]



            is_destructive_cmd = any(re.search(pat, normalized_cmd.lower()) for pat in dangerous_patterns)



            needs_confirm = should_ask(is_destructive=is_destructive_cmd)







            prompt_msg = f"DeepSeek запрашивает ВЫПОЛНЕНИЕ В КОНСОЛИ:\n\n💻 Команда: {normalized_cmd}\n\nРазрешить?"



            



            if not needs_confirm or ask_user_confirmation("Подтверждение: Команда консоли", prompt_msg):



                try:



                    # Detect long-running dev servers (they must not block HTTP execution!)



                    server_signatures = ["http.server", "http-server", "live-server", "vite", "uvicorn", "flask run", "npm start", "npm run dev"]



                    is_bg_server = any(sig in normalized_cmd.lower() for sig in server_signatures)



                    



                    if is_bg_server:



                        print(f"🌐 Запуск локального веб-сервера в фоне: {normalized_cmd}")



                        proc = subprocess.Popen(



                            normalized_cmd,



                            shell=True,



                            cwd=str(DEFAULT_BASE_DIR),



                            creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if sys.platform == "win32" else 0



                        )



                        result = {



                            "status": "success",



                            "output": f"Локальный сервер запущен в фоне (PID: {proc.pid})! Доступен на http://127.0.0.1:8080",



                            "exit_code": 0



                        }



                    else:



                        print(f"⏳ Выполняется: {normalized_cmd}")



                        proc = subprocess.run(



                            normalized_cmd,



                            shell=True,



                            capture_output=True,



                            text=True,



                            cwd=str(DEFAULT_BASE_DIR),



                            timeout=60



                        )



                        output = (proc.stdout + "\n" + proc.stderr).strip()



                        print(f"Результат команды (код {proc.returncode}):\n{output}")



                        



                        tip = ""



                        if proc.returncode != 0:



                            combined = output



                            if "ModuleNotFoundError" in combined or "No module named" in combined:



                                m = re.search(r"No module named ['\"]([^'\"]+)['\"]", combined)



                                mod = m.group(1) if m else "библиотеку"



                                tip = f"\n💡 ДЕЙСТВИЕ ДЛЯ DEEPSEEK: Отсутствует библиотека '{mod}'. Установи её: <<<ACTION: RUN_COMMAND | CMD: pip install {mod}>>> и повтори запуск!"



                            elif "SyntaxError" in combined or "IndentationError" in combined:



                                tip = "\n💡 ДЕЙСТВИЕ ДЛЯ DEEPSEEK: Синтаксическая ошибка в коде. Исправь код и перезапиши файл через WRITE_FILE!"



                            elif "Address already in use" in combined or "Only one usage of each socket address" in combined:



                                tip = "\n💡 ДЕЙСТВИЕ ДЛЯ DEEPSEEK: Порт уже занят. Смени порт сервера на свободный (например, 5001, 8081, 3000)!"



    



                        result = {



                            "status": "success" if proc.returncode == 0 else "error",



                            "output": output + tip if output else ("Команда успешно выполнена (вывода нет)" if proc.returncode == 0 else "Команда завершилась с ошибкой"),



                            "exit_code": proc.returncode



                        }



                except subprocess.TimeoutExpired:



                    result = {



                        "status": "success",



                        "output": "Команда выполняется в фоновом режиме (время ожидания консоли истекло, процесс запущен).",



                        "exit_code": 0



                    }



                except Exception as ex:



                    print(f"❌ Ошибка выполнения команды: {ex}")



                    result = {"status": "error", "message": f"Ошибка запуска команды: {str(ex)}"}



            else:



                result = {"status": "rejected", "message": "Выполнение команды отклонено пользователем"}







        # 13. MCP_CALL



        
        # 14. GET_ICON (Direct Action for SVG icons)
        elif action_type == "GET_ICON":
            name = data.get("name", "check")
            color = data.get("color", "currentColor")
            size = int(data.get("size", 24))
            save_path = data.get("save_path", "")
            print(f"🎨 Запрос иконки: {name} ({color}, {size}px)")
            result = mcp_mgr.call_tool("web_search", "get_svg_icon", {"name": name, "color": color, "size": size, "save_path": save_path})

        # 15. ANALYZE_WEBSITE (Direct Action for Competitor Analysis)
        elif action_type == "ANALYZE_WEBSITE":
            url = data.get("url", "")
            print(f"🌐 Анализ сайта-референса: {url}")
            result = mcp_mgr.call_tool("web_search", "analyze_website", {"url": url})

        elif action_type == "MCP_CALL":



            server_name = data.get("server", "").strip()



            tool_name = data.get("tool", "").strip()



            raw_args = data.get("args", {})



            if isinstance(raw_args, str):



                try:



                    args = json.loads(raw_args)



                except Exception:



                    args = {}



            else:



                args = raw_args



            needs_confirm = should_ask(is_destructive=False)



            prompt_msg = f"DeepSeek запрашивает вызов MCP инструмента:\n\n🔌 Сервер: {server_name}\n🔧 Инструмент: {tool_name}\n\nРазрешить вызов?"



            if not needs_confirm or ask_user_confirmation("Подтверждение: MCP инструмент", prompt_msg):



                print(f"🔌 MCP Вызов: [{server_name} -> {tool_name}] с аргументами: {args}")



                result = mcp_mgr.call_tool(server_name, tool_name, args)



            else:



                result = {"status": "rejected", "message": "Вызов MCP инструмента отклонен пользователем"}







        # 14. MCP_LIST_TOOLS



        elif action_type == "MCP_LIST_TOOLS":



            print("🔌 Запрос списка инструментов MCP")



            tools_desc = mcp_mgr.list_all_tools()



            result = {



                "status": "success",



                "content": tools_desc,



                "message": "Список доступных MCP инструментов получен"



            }







        else:



            result = {"status": "error", "message": f"Неизвестное действие: {action_type}"}







        try:



            log_entry = f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] [ACTION: {action_type}] [MODE: {mode}] [DATA: {data}] -> [RESULT: {result}]\n"



            log_path = Path(__file__).resolve().parent / "action_debug.log"



            with open(log_path, "a", encoding="utf-8") as lf:



                lf.write(log_entry)



        except Exception:



            pass







        self.send_response(200)



        self._send_cors_headers()



        self.send_header("Content-Type", "application/json; charset=utf-8")



        self.end_headers()



        self.wfile.write(json.dumps(result, ensure_ascii=False).encode("utf-8"))







def start_file_watcher():



    """Background watcher that automatically restarts the server if agent_server.py or mcp_config.json is updated."""



    server_file = Path(__file__).resolve()



    cfg_file = server_file.parent / "mcp_config.json"



    try:



        last_mtime = server_file.stat().st_mtime



        last_cfg_mtime = cfg_file.stat().st_mtime if cfg_file.exists() else 0



    except Exception:



        return







    while True:



        time.sleep(2)



        try:



            curr_mtime = server_file.stat().st_mtime



            curr_cfg = cfg_file.stat().st_mtime if cfg_file.exists() else 0



            if curr_mtime != last_mtime or curr_cfg != last_cfg_mtime:



                print("\n" + "=" * 65)



                print("🔄 Обнаружены изменения файлов сервера! Авто-перезапуск...")



                print("=" * 65)



                subprocess.Popen([sys.executable, "-u", str(server_file)], cwd=str(server_file.parent))



                os._exit(0)



        except Exception:



            pass







def run():



    server_address = ("127.0.0.1", PORT)



    ThreadingHTTPServer.allow_reuse_address = True



    httpd = ThreadingHTTPServer(server_address, AgentHandler)



    threading.Thread(target=start_file_watcher, daemon=True).start()



    print("=" * 65)



    print(f"🚀 Локальный Агент Pro + MCP запущен на http://127.0.0.1:{PORT}")



    print(f"📁 Рабочая зона (Desktop): {DEFAULT_BASE_DIR}")



    print(f"💾 Папка бэкапов (UNDO): {BACKUPS_DIR}")



    print("🛡️ Режимы: 🛡️ Защищенный | ⚖️ Стандартный (Автопилот) | ⚡ Турбо")



    print("🔌 Поддержка MCP: Model Context Protocol (system_info, web_search, sqlite_db)")



    print("♻️ Поддержка Корзины: RESTORE_FILE, LIST_TRASH, RENAME (файлы и папки)")



    print("🔄 Горячая перезагрузка (Auto-Reload): АКТИВНА")



    print("=" * 65)



    try:



        httpd.serve_forever()



    except KeyboardInterrupt:



        print("\nОстановка сервера...")



        httpd.server_close()







if __name__ == "__main__":



    run()
