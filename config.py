# config.py
import os
from dotenv import load_dotenv, find_dotenv

# .env 자동 탐색 및 로드 (프로젝트 루트)
load_dotenv(find_dotenv())

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
SQLALCHEMY_DATABASE_URI = os.getenv("DATABASE_URL", "sqlite:///secagent.db")
SQLALCHEMY_TRACK_MODIFICATIONS = False

AGENT_DRY_RUN = os.getenv("AGENT_DRY_RUN", "true").lower() == "true"
DEFAULT_TARGET = os.getenv("DEMO_TARGET", "https://example.com")

SSH_HOST = os.getenv("SSH_HOST", "localhost")
SSH_USER = os.getenv("SSH_USER", "ubuntu")
SSH_KEY  = os.getenv("SSH_KEY")

DB_HOST = os.getenv("DB_HOST", "localhost")
DB_USER = os.getenv("DB_USER", "readonly")
DB_PASS = os.getenv("DB_PASS", "")
DB_PORT = int(os.getenv("DB_PORT", "3306"))
