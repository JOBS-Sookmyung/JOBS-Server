from fastapi import APIRouter, HTTPException, Depends, Query, Request
from sqlalchemy.orm import Session
from db import SessionLocal, InterviewSessionDB, ChatMessageDB
from utils.interview import InterviewSession
from pydantic import BaseModel
from routers.pdf_storage import pdf_storage
from typing import List, Optional, Dict
from datetime import datetime, timedelta
import uuid
import logging

logger = logging.getLogger(__name__)

# 세션 저장소
session_store: Dict[str, InterviewSession] = {}

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
    user_id: str

class ChatSession(BaseModel):
    session_token: str
    created_at: datetime
    status: str
    last_message: Optional[str] = None
    last_message_type: Optional[str] = None

async def create_new_session(db: Session, session_token: str, user_id: str):
    """ 새로운 세션을 생성하고 첫 번째 질문을 저장하는 함수 """
    session = InterviewSessionDB(
        session_token=session_token,
        user_id=user_id,  # 유저 아이디 추가
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


@chat.get("/{token}")
async def get_chat(token: str, db: Session = Depends(get_db)):
    """특정 세션의 채팅 내역을 조회합니다."""
    try:
        # 세션 조회
        session = db.query(InterviewSessionDB).filter(InterviewSessionDB.session_token == token).first()
        if not session:
            session = await create_new_session(db, token)
        
        # 세션의 모든 메시지 조회 (session_id 사용)
        messages = db.query(ChatMessageDB)\
            .filter(ChatMessageDB.session_id == session.id)\
            .order_by(ChatMessageDB.created_at.asc())\
            .all()
        
        # 메시지 타입별 우선순위 정의
        type_priority = {
            "main_question": 1,
            "user_answer": 2,
            "feedback": 3,
            "follow_up": 4
        }
        
        # 메시지를 시간순으로 정렬하되, 같은 시간대의 메시지는 타입 우선순위에 따라 정렬
        sorted_messages = []
        for msg in messages:
            sorted_messages.append({
                "type": msg.message_type,
                "text": msg.content,
                "timestamp": msg.created_at,
                "priority": type_priority.get(msg.message_type, 5)
            })
        
        # 시간순으로 정렬하되, 같은 시간대의 메시지는 타입 우선순위에 따라 정렬
        sorted_messages.sort(key=lambda x: (x["timestamp"], x["priority"]))
        
        # 우선순위 필드 제거
        for msg in sorted_messages:
            del msg["priority"]
        
        # 메시지 목록 반환
        return {
            "session_token": token,
            "messages": sorted_messages,
            "status": session.status
        }
        
    except Exception as e:
        logger.error(f"채팅 내역 조회 중 오류 발생: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@chat.get("/get_chat")
async def get_chat(session_token: str):
    """채팅 내역을 새로고침할 때 사용되는 엔드포인트"""
    try:
        db = SessionLocal()
        try:
            # 세션 조회
            session = db.query(InterviewSessionDB).filter_by(session_token=session_token).first()
            if not session:
                raise HTTPException(status_code=404, detail="세션을 찾을 수 없습니다.")

            # 메시지 조회
            messages = db.query(ChatMessageDB)\
                .filter_by(session_id=session.id)\
                .order_by(ChatMessageDB.created_at.asc())\
                .all()
            
            # 메시지 타입별 우선순위 정의
            type_priority = {
                "main_question": 1,
                "user_answer": 2,
                "feedback": 3,
                "follow_up": 4
            }
            
            # 메시지를 시간순으로 정렬하되, 같은 시간대의 메시지는 타입 우선순위에 따라 정렬
            sorted_messages = []
            for msg in messages:
                sorted_messages.append({
                    "type": msg.message_type,
                    "text": msg.content,
                    "timestamp": msg.created_at,
                    "priority": type_priority.get(msg.message_type, 5)
                })
            
            # 시간순으로 정렬하되, 같은 시간대의 메시지는 타입 우선순위에 따라 정렬
            sorted_messages.sort(key=lambda x: (x["timestamp"], x["priority"]))
            
            # 우선순위 필드 제거
            for msg in sorted_messages:
                del msg["priority"]
            
            return {
                "status": "success",
                "messages": sorted_messages
            }
            
        finally:
            db.close()
            
    except Exception as e:
        logger.error(f"채팅 내역 조회 중 오류 발생: {str(e)}")
        raise HTTPException(status_code=500, detail="채팅 내역을 조회할 수 없습니다.")

@chat.post("/answer/{token}")
async def submit_answer(token: str, request: AnswerRequest, db: Session = Depends(get_db)):
    try:
        session = db.query(InterviewSessionDB).filter_by(session_token=token).first()
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")

        if session.status != "in_progress":
            raise HTTPException(status_code=400, detail="This session is not active")

        interview_session = InterviewSession(token=token)
        
        # 사용자 답변 저장 (session_id 사용)
        user_message = ChatMessageDB(
            session_id=session.id,
            message_type="user_answer",
            content=request.answer
        )
        db.add(user_message)
        
        # 피드백 생성
        feedback = await interview_session.generate_feedback(request.answer)
        if not feedback:
            raise HTTPException(status_code=500, detail="피드백을 생성할 수 없습니다.")
            
        feedback_message = ChatMessageDB(
            session_id=session.id,
            message_type="feedback",
            content=feedback
        )
        db.add(feedback_message)
        db.commit()
        
        return {"feedback": feedback}
    except Exception as e:
        db.rollback()
        logger.error(f"답변 제출 중 오류: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@chat.post("/follow-up/{token}")
async def get_follow_up_question(token: str, request: FollowUpRequest, db: Session = Depends(get_db)):
    try:
        session = db.query(InterviewSessionDB).filter_by(session_token=token).first()
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")

        if session.status != "in_progress":
            raise HTTPException(status_code=400, detail="This session is not active")

        interview_session = InterviewSession(token=token)
        
        # 현재 꼬리질문 진행 상태 확인
        if session.current_follow_up_index >= 2:
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
            # 꼬리질문 저장 (session_id 사용)
            follow_up_message = ChatMessageDB(
                session_id=session.id,
                message_type="follow_up",
                content=follow_up
            )
            db.add(follow_up_message)
            session.current_follow_up_index += 1
            db.commit()
            
            return {
                "question": follow_up, 
                "type": "follow_up", 
                "follow_up_count": session.current_follow_up_index
            }
        
        return {"question": None, "type": "no_question"}
    except Exception as e:
        db.rollback()
        logger.error(f"꼬리질문 생성 중 오류: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@chat.get("/all/sessions")
async def get_sessions(user_id: str, db: Session = Depends(get_db)):
    try:
        # 유저 ID를 기준으로 세션을 필터링 (최신순)
        sessions = db.query(InterviewSessionDB)\
            .filter(InterviewSessionDB.user_id == user_id)\
            .order_by(InterviewSessionDB.created_at.desc())\
            .all()

        # 세션 정보를 JSON 형태로 변환
        session_list = []
        for session in sessions:
            # 해당 세션의 메시지들을 조회 (session_id 사용)
            messages = db.query(ChatMessageDB)\
                .filter(ChatMessageDB.session_id == session.id)\
                .order_by(ChatMessageDB.created_at.desc())\
                .all()

            # 마지막 메시지 가져오기
            last_message = messages[0].content if messages else None

            # 대표질문 개수 계산
            main_questions = [msg for msg in messages if msg.message_type == "main_question"]

            session_list.append({
                "session_token": session.session_token,
                "status": session.status,
                "created_at": session.created_at,
                "last_message": last_message,
                "current_question": len(main_questions)
            })

        return session_list
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))




@chat.post("/start/{pdf_token}")
async def start_chat(pdf_token: str, request: StartChatRequest, db: Session = Depends(get_db)):
    """새로운 채팅 세션을 시작하는 API"""
    try:
        # PDF 토큰 존재 여부 확인
        logger.info(f"PDF 토큰으로 데이터 조회 시도: {pdf_token}")
        pdf_data = pdf_storage.get_pdf(pdf_token)
        if not pdf_data:
            logger.error(f"PDF 데이터를 찾을 수 없음: {pdf_token}")
            raise HTTPException(
                status_code=400,
                detail="PDF 데이터를 찾을 수 없습니다."
            )

        # 기존 세션이 있는지 확인
        existing_session = db.query(InterviewSessionDB).filter_by(
            session_token=pdf_token
        ).first()
        
        if existing_session:
            logger.info(f"기존 세션 발견: {pdf_token}")
            return {"session_token": pdf_token}

        # 새 세션 생성
        try:
            logger.info(f"새 세션 생성 시도: {pdf_token}")
            session = await create_new_session(db, pdf_token, request.user_id)  # 유저 아이디 전달
            logger.info(f"새 세션 생성 성공: {pdf_token}")
            return {"session_token": pdf_token}
        except Exception as e:
            logger.error(f"세션 생성 중 오류 발생: {str(e)}")
            db.rollback()
            raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        logger.error(f"채팅 시작 중 오류 발생: {str(e)}")
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
