import os

HOST = "0.0.0.0"
RHOST = HOST.replace(".", "\\.")
PORT = 8080
CPORT = 3000
ORIGIN_REGEX = f"^(https?://)?({RHOST}|localhost)(:({PORT}|{CPORT}|80|443))?(/.*)?$"

CURR_DIR = os.getcwd()
FILE_DIR = os.path.join(CURR_DIR, "files")
MAX_FSIZE = 50 * 1024 * 1024 # 50MB
