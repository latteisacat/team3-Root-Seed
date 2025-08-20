import os

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
SQLALCHEMY_DATABASE_URI = os.getenv("DATABASE_URL", "sqlite:///secagent.db")
SQLALCHEMY_TRACK_MODIFICATIONS = False

# Agent behavior
AGENT_DRY_RUN = os.getenv("AGENT_DRY_RUN", "true").lower() == "true"
DEFAULT_TARGET = os.getenv("DEMO_TARGET", "https://example.com")

# SSH defaults (used only when AGENT_DRY_RUN=false and ssh_exec called)
SSH_HOST = os.getenv("SSH_HOST", "localhost")
SSH_USER = os.getenv("SSH_USER", "ubuntu")
SSH_KEY = os.getenv("SSH_KEY")  # path to private key, e.g. /home/ubuntu/.ssh/id_rsa

# MariaDB defaults (used only when AGENT_DRY_RUN=false and mariadb_query called)
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_USER = os.getenv("DB_USER", "readonly")
DB_PASS = os.getenv("DB_PASS", "")
DB_PORT = int(os.getenv("DB_PORT", "3306"))
