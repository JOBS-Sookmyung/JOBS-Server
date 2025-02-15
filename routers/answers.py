import os, sys
sys.path.append(os.path.dirname(os.path.abspath(os.path.dirname(__file__))))

from fastapi import APIRouter
from fastapi import Response, Cookie
from fastapi import Form
# from pydantic import BaseModel
from routers import pdf_files
from utils import echo, InterviewSession

# 인터뷰 세션 목록 초기화
interview_sessions = {}

# answers page에서 api 정의
answers = APIRouter(prefix="/answers", tags=["answers"])


@answers.get("/")
async def start_interview(token: str = Cookie(None)):
    if not token:
        raise echo(400, "토큰이 필요합니다.")
    
    # 토큰 기반 PDF 확인
    if token not in pdf_files:
        raise echo(404, "해당 토큰에 대한 PDF 파일이 존재하지 않습니다.")

    # 세션이 없으면 자동 생성
    if "session" not in pdf_files[token]:
        pdf_files[token]["session"] = InterviewSession(token=token, question_num=5)

    session = pdf_files[token]["session"]
    question = await session.generate_next_question()

    # if not question:
    #     return {"message": "모든 질문이 완료되었습니다."}

    return {"question": question}


@answers.post("/")
async def submit_answer(
    token: str = Cookie(None), # 사용자 구분용 토큰
    answer: str = Form()
):
    if not token or token not in pdf_files:
        raise echo(404, "세션이 존재하지 않습니다. 먼저 /answers/를 호출해주세요.")
    
    if "session" not in pdf_files[token]:
        raise echo(404, "세션이 존재하지 않습니다. 먼저 /answers/를 호출해주세요.")

    if not answer:
        raise echo(400, "답변이 비어있습니다.")

    session = pdf_files[token]["session"]
    await session.add_answer(answer)

    next_question = await session.generate_next_question()
    if not next_question:
        return {"message": "인터뷰가 완료되었습니다."}

    return {"question": next_question}

