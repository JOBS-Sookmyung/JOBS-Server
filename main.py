from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routers import input, questions, answers, recommendations
from config import HOST, PORT, ORIGIN_REGEX
from utils import clean_files
import uvicorn, atexit

app = FastAPI(title="JOBS-Server", version="0.2.0")

# CORS 설정 허용
app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=ORIGIN_REGEX,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 라우트 설정
app.include_router(input)
app.include_router(questions)
app.include_router(answers)
app.include_router(recommendations)

# 종료 시 clean file 후 종료 설정
if __name__ == "__main__":
    atexit.register(clean_files)
    uvicorn.run("main:app", host=HOST, port=PORT, reload=False)
