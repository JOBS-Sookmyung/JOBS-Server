from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routers import input  # questions 제거
from config import HOST, PORT, ORIGIN_REGEX
from utils import clean_files
from routers.login import router as login_router
from db import create_tables
from routers.chat import chat
from routers.recommendations import recommendations  # 추가
import uvicorn
import atexit
import asyncio
#from utils.extract_video import process_videos, vectorize_and_save  # 영상 추출 및 벡터화 함수 가져오기

app = FastAPI(title="JOBS-Server", version="0.2.0")

origins = ["http://localhost:8000", "http://localhost:3000"]

# CORS 설정 허용
app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=ORIGIN_REGEX,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    allow_origins=origins,
)

# 라우트 설정
app.include_router(input)
app.include_router(chat)
app.include_router(login_router, prefix="", tags=["auth"])
app.include_router(recommendations)  # 추가

""" # 서버 시작 시 영상 추출 및 벡터화 작업 실행 -> 미리 영상들을 벡터 디비에 다 넣어놓고 서버 시작
@app.on_event("startup")
async def startup_event():
    # 영상 추출 작업 후 벡터화 작업 실행 순서 보장
    await process_videos()  # 영상 추출 후
    await vectorize_and_save()  # 그 후 벡터화 작업 실행
 """
 # 서버 시작 시 실행할 로직 - DB 테이블 생성
@app.on_event("startup")
async def startup_event():
    create_tables()  # db.py 안의 create_tables()
   
# 종료 시 clean file 후 종료 설정
if __name__ == "__main__":
    atexit.register(clean_files)
    uvicorn.run("main:app", host=HOST, port=PORT, reload=False)
