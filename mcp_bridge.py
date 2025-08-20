# Minimal MCP-like bridge with safe defaults.
# http_check: real; ssh_exec & mariadb_query: stubs unless AGENT_DRY_RUN=false.
import hashlib, json, time
import requests
import paramiko
import pymysql
from config import AGENT_DRY_RUN, SSH_HOST, SSH_USER, SSH_KEY, DB_HOST, DB_USER, DB_PASS, DB_PORT

def _sha256(data: bytes) -> str:
    h = hashlib.sha256(); h.update(data); return h.hexdigest()

def http_check(url: str, timeout: int = 10):
    t0 = time.time()
    r = requests.get(url, timeout=timeout, allow_redirects=False)
    info = {
        "url": url,
        "status": r.status_code,
        "headers": dict(r.headers),
        "text_sample": r.text[:512],
        "elapsed_ms": int((time.time() - t0) * 1000),
    }
    raw = json.dumps(info, ensure_ascii=False).encode()
    return {"tool":"http_check", "args":{"url":url}, "result":info, "sha256":_sha256(raw)}

def ssh_exec(cmd: str):
    if AGENT_DRY_RUN:
        # Safe stub output
        info = {"cmd": cmd, "stdout": "DRY_RUN: no-op", "stderr": "", "code": 0}
        raw = json.dumps(info).encode()
        return {"tool":"ssh_exec", "args":{"cmd":cmd}, "result": info, "sha256": _sha256(raw)}
    # Real SSH (key-based)
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(SSH_HOST, username=SSH_USER, key_filename=SSH_KEY, timeout=8)
    stdin, stdout, stderr = client.exec_command(cmd, timeout=10)
    out, err = stdout.read().decode(), stderr.read().decode()
    code = stdout.channel.recv_exit_status()
    client.close()
    info = {"cmd": cmd, "stdout": out, "stderr": err, "code": code}
    raw = json.dumps(info).encode()
    return {"tool":"ssh_exec", "args":{"cmd":cmd}, "result": info, "sha256": _sha256(raw)}

def mariadb_query(sql: str):
    if AGENT_DRY_RUN:
        info = {"sql": sql, "rows": [], "cols": [], "note":"DRY_RUN: no DB connection"}
        raw = json.dumps(info).encode()
        return {"tool":"mariadb_query","args":{"sql":sql},"result":info,"sha256":_sha256(raw)}
    conn = pymysql.connect(host=DB_HOST, user=DB_USER, password=DB_PASS, port=DB_PORT, connect_timeout=5)
    cur = conn.cursor()
    cur.execute(sql)
    rows = cur.fetchall()
    cols = [d[0] for d in cur.description] if cur.description else []
    cur.close(); conn.close()
    info = {"sql": sql, "rows": rows, "cols": cols}
    raw = json.dumps(info).encode()
    return {"tool":"mariadb_query","args":{"sql":sql},"result":info,"sha256":_sha256(raw)}
