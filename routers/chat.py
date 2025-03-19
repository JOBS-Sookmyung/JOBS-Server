from fastapi import APIRouter, HTTPException, Depends, Query
from sqlalchemy.orm import Session
from db import SessionLocal, InterviewSessionDB, ChatMessageDB
from utils.interview import InterviewSession
from pydantic import BaseModel
from routers.pdf_storage import pdf_storage
from typing import List, Optional
from datetime import datetime, timedelta
import uuid

chat = APIRouter(prefix="/chat", tags=["chat"])

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

class ChatResponse(BaseModel):
    messages: List[dict]

class AnswerRequest(BaseModel):
    answer: str

class FollowUpRequest(BaseModel):
    previous_answer: str

class StartChatRequest(BaseModel):
    pdf_token: str

async def create_new_session(db: Session, session_token: str):
    """ 새로운 세션을 생성하고 첫 번째 질문을 저장하는 함수 """
    session = InterviewSessionDB(
        session_token=session_token,
        status="in_progress",
        current_main_question_index=0,
        current_follow_up_index=0
    )
    db.add(session)
    db.commit()
    db.refresh(session)

    interview_session = InterviewSession(token=session_token)
    first_question = await interview_session.generate_main_question()
    
    if not first_question:
        raise HTTPException(status_code=500, detail="대표질문을 생성할 수 없습니다.")

    message = ChatMessageDB(
        session_id=session.id,
        message_type="main_question",
        content=first_question
    )
    db.add(message)
    db.commit()
    
    return session

@chat.get("/", response_model=ChatResponse)
async def get_chat(session_token: str, db: Session = Depends(get_db)):
    """ 채팅 내역을 가져오는 API """
    session = db.query(InterviewSessionDB).filter_by(session_token=session_token).first()
    
    if not session:
        session = await create_new_session(db, session_token)

    messages = db.query(ChatMessageDB).filter_by(session_id=session.id).order_by(ChatMessageDB.created_at).all()
    return {"messages": [{"type": msg.message_type, "text": msg.content} for msg in messages]}

@chat.post("/answer/{token}")
async def submit_answer(token: str, request: AnswerRequest, db: Session = Depends(get_db)):
    session = db.query(InterviewSessionDB).filter_by(session_token=token).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    if session.status != "in_progress":
        raise HTTPException(status_code=400, detail="This session is not active")

    interview_session = InterviewSession(token=token)
    
    # 사용자 답변 저장
    user_message = ChatMessageDB(session_id=session.id, message_type="user_answer", content=request.answer)
    db.add(user_message)
    
    # 피드백 생성
    feedback = await interview_session.generate_feedback(request.answer)
    feedback_message = ChatMessageDB(session_id=session.id, message_type="feedback", content=feedback)
    db.add(feedback_message)
    db.commit()
    
    return {"feedback": feedback}

@chat.post("/follow-up/{token}")
async def get_follow_up_question(token: str, request: FollowUpRequest, db: Session = Depends(get_db)):
    session = db.query(InterviewSessionDB).filter_by(session_token=token).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    if session.status != "in_progress":
        raise HTTPException(status_code=400, detail="This session is not active")

    interview_session = InterviewSession(token=token)
    
    # 현재 꼬리질문 진행 상태 확인
    if session.current_follow_up_index >= 2: #꼬리질문 개수 조정 (시험을 위해 2개로 조정)
        # 꼬리질문 한도 도달 시 다음 대표질문으로 전환
        session.current_follow_up_index = 0
        session.current_main_question_index += 1
        db.commit()

        if session.current_main_question_index < 5:
            next_question = await interview_session.generate_main_question()
            if next_question:
                next_main_question = ChatMessageDB(
                    session_id=session.id,
                    message_type="main_question",
                    content=next_question
                )
                db.add(next_main_question)
                db.commit()
                return {"question": next_question, "type": "main_question"}
        else:
            session.status = "completed"
            db.commit()
            return {"question": None, "type": "completed"}
    
    # 꼬리질문 생성
    follow_up = await interview_session.generate_follow_up(request.previous_answer)
    
    if follow_up:
        # 꼬리질문 저장
        follow_up_message = ChatMessageDB(
            session_id=session.id,
            message_type="follow_up",
            content=follow_up
        )
        db.add(follow_up_message)
        session.current_follow_up_index += 1
        db.commit()
        
        return {"question": follow_up, "type": "follow_up", "follow_up_count": session.current_follow_up_index}
    
    return {"question": None, "type": "no_question"}

@chat.get("/sessions")
async def get_sessions(user_id: str, db: Session = Depends(get_db)):
    try:
        # 사용자의 모든 세션 가져오기
        sessions = db.query(InterviewSessionDB).filter(
            InterviewSessionDB.user_id == user_id
        ).order_by(InterviewSessionDB.created_at.desc()).all()
        
        return {
            "sessions": [
                {
                    "id": session.id,
                    "session_token": session.session_token,
                    "created_at": session.created_at,
                    "current_question_index": session.current_question_index
                }
                for session in sessions
            ]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@chat.post("/start/{pdf_token}")
async def start_chat(pdf_token: str, db: Session = Depends(get_db)):
    """새로운 채팅 세션을 시작하는 API"""
    try:
        # PDF 토큰 존재 여부 확인
        pdf_data = pdf_storage.get_pdf(pdf_token)
        if not pdf_data:
            raise HTTPException(
                status_code=400,
                detail="PDF 데이터를 찾을 수 없습니다."
            )

        # 기존 세션이 있는지 확인
        existing_session = db.query(InterviewSessionDB).filter_by(
            session_token=pdf_token
        ).first()
        
        if existing_session:
            return {"session_token": pdf_token}

        # 새 세션 생성 및 첫 질문 생성
        session = await create_new_session(db, pdf_token)
        
        return {"session_token": pdf_token}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

@chat.post("/cleanup")
async def cleanup_sessions(db: Session = Depends(get_db)):
    """ 오래된 세션들을 정리하는 API """
    try:
        # 완료된 세션 삭제
        completed_sessions = db.query(InterviewSessionDB).filter_by(status="completed").all()
        for session in completed_sessions:
            db.query(ChatMessageDB).filter_by(session_id=session.id).delete()
            db.delete(session)
        
        # 24시간 이상 된 세션 삭제
        old_sessions = db.query(InterviewSessionDB).filter(
            InterviewSessionDB.created_at < datetime.now() - timedelta(hours=24)
        ).all()
        for session in old_sessions:
            db.query(ChatMessageDB).filter_by(session_id=session.id).delete()
            db.delete(session)
        
        db.commit()
        return {"message": "세션 정리 완료"}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))
