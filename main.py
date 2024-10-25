from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routers import input
from config import HOST, PORT, ORIGIN_REGEX
from utils import clean_files
import uvicorn, atexit

app = FastAPI(title="JOBS-Server", version="0.2.0")

app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=ORIGIN_REGEX,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(input)

if __name__ == "__main__":
    atexit.register(clean_files)
    uvicorn.run("main:app", host=HOST, port=PORT, reload=False)
