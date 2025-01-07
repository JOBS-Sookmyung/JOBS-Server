import os, sys
sys.path.append(os.path.dirname(os.path.abspath(os.path.dirname(__file__))))

from fastapi import APIRouter
from fastapi import Response, Cookie
from fastapi import File, Form, UploadFile
# from pydantic import BaseModel
from config import FILE_DIR, MAX_FSIZE
from utils import echo
import random

questions = APIRouter(prefix="/questions", tags=["questions"])


@questions.get("/")
async def get_questions():
    random_qlist = []

    for i in range(1, 6):
        random_q = f"Q{i}. "

        for j in range(1, 50):
            random_q += chr(random.randint(33, 126))
        
        random_q += "?"
        random_qlist.append(random_q)
        # print(random_q)

    return random_qlist

