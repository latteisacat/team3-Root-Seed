## AI를 활용한 취약점 분석 자동화 도구.

RAG (Retrieval-Augmented Generation 검색 증강 생성) 활용.
이를 바탕으로 Prompt 재구성. [Prompt Engineering + IKE (In-Context Learning Knowledge Editing)]
해당 Prompt 를 바탕으로 MCP 연결 → 원하는 정보 도출. 


### 프로그램 동작 예시 

* 사용자가 “U31 점검해”라고 하면,
* **RAG**가 U31에 해당하는 점검 지식(무엇을 확인해야 하는지)을 찾아주고,
* **LLM**이 그 지식을 토대로 “어떤 MCP 툴을 호출할지” 스스로 정한 뒤,
* **MCP**가 실제 서버에 접속해 데이터를 가져오고,
* 다시 **LLM**이 기준과 증거를 맞춰 판정·리포트를 작성합니다.

---

## 1. RAG 단계

* **사용자 요청**: *“문서에 적힌 U31번 취약점 점검해줘.”*
* **RAG 검색**:

  * 사내 보안 기준/점검 문서 중에서 “U31번 취약점”을 찾아 관련 내용을 꺼냅니다.
  * 예:

    ```
    [U31] Apache HTTP Server 보안 헤더 미설정
    - 점검 방법: 응답 헤더 중 Strict-Transport-Security, X-Frame-Options 확인
    - 기준: 반드시 설정되어야 함
    - 개선: Apache 설정 파일에 Header set ... 추가
    ```

---

## 2. 프롬프트 엔지니어링

* 모델에게 이렇게 “역할+규칙”을 줍니다:

  * “네 역할은 보안 점검 오퍼레이터.

    * 주어진 증거가 없으면 MCP 도구를 사용해 수집할 것.
    * 수집할 명령/쿼리는 RAG로 검색된 점검 방법을 기준으로 정할 것.”

---

## 3. MCP 호출 자동 생성

* LLM은 RAG에서 꺼낸 “점검 방법”을 읽고, 필요한 MCP 도구 호출을 **계획**합니다.
* 예시로 이런 호출을 만들어냅니다:

  ```json
  {
    "tool": "http_check",
    "args": { "url": "https://target-server" }
  }
  ```
* MCP 서버가 이 호출을 실행 → 실제 웹 서버에 HTTPS 요청 → 응답 헤더와 TLS 정보 반환.

---

## 4. 증거 분석 & 결과 생성

* LLM은 MCP 응답(예: 응답 헤더에 `Strict-Transport-Security` 없음)을 받아,
* RAG 문서 기준과 대조해 “불합격” 판정을 내리고,
* 출력은 규격화된 JSON/PDF 리포트로 만듭니다:

  ```json
  {
    "control_id": "U31",
    "status": "불합격",
    "evidence": { "header": "Strict-Transport-Security 없음" },
    "recommendation": "Apache VirtualHost에 HSTS 헤더 추가"
  }
  ```

---

# MCP-RAG Agent Minimal (Ubuntu + Python + Flask)

A minimal, self-contained example showing how to:
- Create and monitor security checks via a **Flask** web UI
- Run jobs asynchronously with **RQ + Redis**
- Call "MCP-like" tools (`http_check`, `ssh_exec`, `mariadb_query` stubs)
- Store events, artifacts, and findings into **SQLite**
- Stream job logs with **SSE**
- Include a demo control **U31 (HSTS header)** for web servers

> This is a teaching/demo skeleton. Harden and adapt before production.

## Requirements (Ubuntu)

```bash
sudo apt update
sudo apt install -y python3-pip python3-venv redis-server
```

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
export FLASK_APP=app.py
# (Optional) set envs
# export REDIS_URL=redis://localhost:6379/0
# export AGENT_DRY_RUN=true      # skip real SSH/DB calls
# export DEMO_TARGET=https://example.com
flask db_init
redis-server --daemonize yes  # or run it as a service
rq worker jobs &
flask run
```

Open http://127.0.0.1:5000/

## Quick Demo

1. Click **New Job** on the dashboard.
2. Use target from `DEMO_TARGET` or input e.g. `https://example.com`.
3. Add control `U31` (HSTS check).
4. Watch live logs and the final finding; download report JSON.

## Notes
- `ssh_exec` and `mariadb_query` are **safe stubs** by default. Set `AGENT_DRY_RUN=false` to enable real operations.
- For SSH, configure credentials in `config.py` or via environment variables.
- For MariaDB, ensure reachable DB and read-only credentials.

## Project Layout

```
mcp_rag_agent_minimal/
├─ app.py                # Flask routes + SSE + job endpoints
├─ agent.py              # Orchestrates: RAG stub → plan → MCP calls → decide
├─ mcp_bridge.py         # http_check / ssh_exec / mariadb_query (stubs/real)
├─ models.py             # SQLAlchemy models
├─ config.py             # Settings
├─ worker.py             # RQ worker entry
├─ templates/
│  ├─ dashboard.html
│  └─ job.html
├─ static/
│  └─ style.css
├─ requirements.txt
└─ README.md
```

## Security
- Keep **read-only** first. Never run destructive commands.
- Store secrets in a vault (not provided here). This demo uses env variables.
- Review CSP/HSTS for the Flask app if exposed beyond localhost.
