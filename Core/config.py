import os
from pathlib import Path
from dotenv import load_dotenv

ROOT_DIR = Path(__file__).resolve().parent.parent
load_dotenv(dotenv_path=ROOT_DIR / '.env')

def get_env_escaped(key: str, default: str = "") -> str:
    val = os.getenv(key, default)
    if val:
        try:
            return val.encode().decode('unicode_escape').strip("'")
        except Exception:
            return val.strip("'")
    return default

MASTER_KEY = get_env_escaped('MASTER_KEY', 'default_master_key')
MONGODB_URI = get_env_escaped('MONGODB_URI', 'mongodb://localhost:27017/?replicaSet=rs0')
REDIS_URL = get_env_escaped('REDIS_URL', 'redis://localhost:6379')
TELEGRAM_BOT_TOKEN = get_env_escaped('TELEGRAM_BOT_TOKEN', '')
CHROMA_PATH = get_env_escaped('CHROMA_PATH', '/var/lib/chroma_data')
PLAYWRIGHT_BROWSERS_PATH = get_env_escaped('PLAYWRIGHT_BROWSERS_PATH', '/var/lib/playwright')

os.makedirs('/var/lib/ai_business_os/temp/', exist_ok=True)
os.makedirs(CHROMA_PATH, exist_ok=True)

# ========== CẤU HÌNH MỚI ==========
DRY_RUN_MODE = os.getenv("DRY_RUN_MODE", "false").lower() == "true"
DEFAULT_MODEL_PRIORITY = os.getenv("DEFAULT_MODEL_PRIORITY", "gemini/gemini-1.5-flash,deepseek/deepseek-chat,openrouter/openai/gpt-4o-mini,gpt-4o-mini").split(',')
BUDGET_WARNING_THRESHOLD = float(os.getenv("BUDGET_WARNING_THRESHOLD", "0.8"))
