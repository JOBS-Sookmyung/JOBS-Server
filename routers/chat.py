from fastapi import APIRouter, HTTPException, Depends, WebSocket, WebSocketDisconnect
from sqlalchemy.orm import Session
from db import SessionLocal, InterviewSessionDB, MainQuestionDB
from utils.interview import InterviewSession
from pydantic import BaseModel
from routers.pdf_storage import pdf_storage
from typing import List

chat = APIRouter(prefix="/chat", tags=["chat"])

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

class ChatResponse(BaseModel):
    questions: List[str]

@chat.get("/", response_model=ChatResponse)
async def get_main_questions(session_token: str, db: Session = Depends(get_db)):
    """ 대표 질문 5개를 가져오는 API """
    # 이력서 데이터 확인
    pdf_data = pdf_storage.get_pdf(session_token)
    if not pdf_data:
        raise HTTPException(status_code=404, detail="🚨 이력서 데이터를 찾을 수 없습니다.")
    
    # 세션 찾기
    session = db.query(InterviewSessionDB).filter_by(session_token=session_token).first()
    if not session:
        raise HTTPException(status_code=404, detail="🚨 인터뷰 세션을 찾을 수 없습니다.")

    # 기존 질문이 있으면 반환, 없으면 생성
    question_entries = db.query(MainQuestionDB).filter_by(session_id=session.id).all()
    if question_entries:
        return {"questions": [q.content for q in question_entries]}

    # 새로운 질문 생성
    interview_session = InterviewSession(token=session_token)
    questions = await interview_session.generate_main_questions(5)  # 5개의 질문 생성

    if not questions:
        raise HTTPException(status_code=500, detail="🚨 대표 질문을 생성할 수 없습니다.")

    return {"questions": questions}

@chat.websocket("/ws/{token}")
async def websocket_endpoint(websocket: WebSocket, token: str):
    await websocket.accept()
    
    try:
        # 이력서 데이터 확인
        pdf_data = pdf_storage.get_pdf(token)
        if not pdf_data:
            raise HTTPException(status_code=404, detail="이력서 데이터를 찾을 수 없습니다.")
        
        # 세션 초기화
        if "session" not in pdf_data:
            pdf_data["session"] = InterviewSession(token=token)
            pdf_storage.add_pdf(token, pdf_data)
        
        session = pdf_data["session"]
        
        while True:
            data = await websocket.receive_text()
            # 나머지 로직...
            
    except WebSocketDisconnect:
        print(f"Client disconnected: {token}")
    except Exception as e:
        print(f"Error: {str(e)}")
        await websocket.close()

@chat.post("/start/{token}")
async def start_interview(token: str):
    # 이력서 데이터 확인
    pdf_data = pdf_storage.get_pdf(token)
    if not pdf_data:
        raise HTTPException(status_code=404, detail="이력서 데이터를 찾을 수 없습니다.")
    
    # 세션 초기화
    if "session" not in pdf_data:
        pdf_data["session"] = InterviewSession(token=token)
        pdf_storage.add_pdf(token, pdf_data)
    
    session = pdf_data["session"]
    return {"message": "인터뷰 세션이 시작되었습니다."}

@chat.post("/answer/{token}")
async def submit_answer(token: str, answer: str):
    # 이력서 데이터 확인
    pdf_data = pdf_storage.get_pdf(token)
    if not pdf_data:
        raise HTTPException(status_code=404, detail="이력서 데이터를 찾을 수 없습니다.")
    
    if "session" not in pdf_data:
        raise HTTPException(status_code=404, detail="세션을 찾을 수 없습니다.")
    
    session = pdf_data["session"]
    # 답변 처리 로직...
    return {"message": "답변이 저장되었습니다."}

@chat.post("/hint/{token}")
async def get_hint(token: str):
    # 이력서 데이터 확인
    pdf_data = pdf_storage.get_pdf(token)
    if not pdf_data:
        raise HTTPException(status_code=404, detail="이력서 데이터를 찾을 수 없습니다.")
    
    if "session" not in pdf_data:
        raise HTTPException(status_code=404, detail="세션을 찾을 수 없습니다.")
    
    session = pdf_data["session"]
    # 힌트 생성 로직...
    return {"hint": "힌트 내용..."}
