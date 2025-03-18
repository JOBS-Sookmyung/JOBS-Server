from fastapi import APIRouter, HTTPException, Depends, WebSocket, WebSocketDisconnect
from sqlalchemy.orm import Session
from db import SessionLocal, InterviewSessionDB, MainQuestionDB
from utils.interview import InterviewSession
from pydantic import BaseModel
from routers.pdf_storage import pdf_storage
from typing import List
from datetime import datetime

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
    
    # 세션 찾기 또는 생성
    session = db.query(InterviewSessionDB).filter_by(session_token=session_token).first()
    if not session:
        # 새로운 세션 생성
        session = InterviewSessionDB(
            session_token=session_token,
            status="in_progress"
        )
        db.add(session)
        db.commit()
        db.refresh(session)
        print(f"✅ 새로운 세션 생성됨 - 토큰: {session_token}")

    # 기존 질문이 있으면 반환, 없으면 생성
    question_entries = db.query(MainQuestionDB).filter_by(session_id=session.id).all()
    if question_entries:
        return {"questions": [q.content for q in question_entries]}

    # 새로운 질문 생성
    interview_session = InterviewSession(token=session_token)
    questions = await interview_session.generate_main_questions(5)  # 5개의 질문 생성

    if not questions:
        raise HTTPException(status_code=500, detail="🚨 대표 질문을 생성할 수 없습니다.")

    # 생성된 질문들을 DB에 저장
    for question in questions:
        main_question = MainQuestionDB(
            session_id=session.id,
            content=question
        )
        db.add(main_question)
    
    db.commit()
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
    
    # 세션 초기화 - 항상 새로운 세션 생성
    pdf_data["session"] = InterviewSession(token=token)
    pdf_data["session_started_at"] = datetime.now().isoformat()
    pdf_storage.add_pdf(token, pdf_data)
    
    return {"message": "인터뷰 세션이 시작되었습니다."}

@chat.post("/end/{token}")
async def end_interview(token: str):
    # 이력서 데이터 확인
    pdf_data = pdf_storage.get_pdf(token)
    if not pdf_data:
        raise HTTPException(status_code=404, detail="이력서 데이터를 찾을 수 없습니다.")
    
    if "session" not in pdf_data:
        raise HTTPException(status_code=404, detail="세션을 찾을 수 없습니다.")
    
    # 세션 종료 처리
    end_time = datetime.now().isoformat()
    pdf_data["session_ended_at"] = end_time
    pdf_storage.add_pdf(token, pdf_data)
    
    # 세션 정보를 응답에 포함
    session_info = {
        "token": token,
        "start_time": pdf_data.get("session_started_at", "시작 시간 없음"),
        "end_time": end_time
    }
    
    return {
        "message": "인터뷰 세션이 종료되었습니다.",
        "session_info": session_info
    }

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

@chat.post("/end-interview")
async def end_interview(token: str):
    """면접 세션을 종료하고 세션 정보를 반환합니다."""
    try:
        # 이력서 데이터 확인
        pdf_data = pdf_storage.get_pdf(token)
        if not pdf_data:
            raise HTTPException(status_code=404, detail="이력서 데이터를 찾을 수 없습니다.")
        
        if "session" not in pdf_data:
            raise HTTPException(status_code=404, detail="세션을 찾을 수 없습니다.")
        
        # 세션 종료 시간 기록
        db = SessionLocal()
        try:
            interview_session = db.query(InterviewSessionDB).filter_by(session_token=token).first()
            if interview_session:
                interview_session.end_time = datetime.now()
                interview_session.status = "completed"  # 세션 상태를 completed로 변경
                db.commit()
                
                # 세션 정보 출력
                session_info = {
                    "session_id": interview_session.id,
                    "start_time": interview_session.start_time,
                    "end_time": interview_session.end_time,
                    "duration": (interview_session.end_time - interview_session.start_time).total_seconds(),
                    "total_questions": len(pdf_data["session"].main_questions)
                }
                print(f"📊 세션 종료: {session_info}")
                
                # PDF 데이터에서 세션 정보 제거
                pdf_data.pop("session", None)
                pdf_data.pop("session_started_at", None)
                pdf_storage.add_pdf(token, pdf_data)
                
                return session_info
            else:
                raise HTTPException(status_code=404, detail="세션을 찾을 수 없습니다.")
        finally:
            db.close()
            
    except Exception as e:
        print(f"❌ 세션 종료 중 오류 발생: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
