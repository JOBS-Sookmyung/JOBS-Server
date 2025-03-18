# 프로젝트 환경 설정을 중앙에서 관리하기 위한 파일
import os
from dotenv import load_dotenv

# 환경변수 정의
HOST = "0.0.0.0"
RHOST = HOST.replace(".", "\\.")
PORT = 8000
CPORT = 3000
ORIGIN_REGEX = f"^(https?://)?({RHOST}|localhost)(:({PORT}|{CPORT}|80|443))?(/.*)?$"

# API URL 추가
API_URL = f"http://{HOST}:{PORT}"  # 또는 "http://localhost:8000"

CURR_DIR = os.getcwd()
# uploads 디렉토리 생성
UPLOAD_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "uploads")
if not os.path.exists(UPLOAD_DIR):
    os.makedirs(UPLOAD_DIR, exist_ok=True)
FILE_DIR = UPLOAD_DIR
MAX_FSIZE = 50 * 1024 * 1024 # 50MB

# .env 파일 로드
load_dotenv()

SQL_URL = os.getenv("SQL_URL", "mysql+pymysql://user:password@localhost:3307/jobs")
NOSQL_URL = os.getenv("NOSQL_URL")

API_KEY = os.getenv("OPENAI_API_KEY")
PAFY_KEY = os.getenv("PAFY_KEY")

# Redis 설정 추가
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
REDIS_SESSION_EXPIRE = 3600  # 세션 만료 시간 (1시간)