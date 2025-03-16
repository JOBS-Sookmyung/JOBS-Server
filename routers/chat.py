from fastapi import APIRouter, Cookie, Form, Depends, UploadFile, Query
from sqlalchemy.orm import Session
from db import get_db, InterviewSessionDB, MainQuestionDB, FollowUpDB, ChatLogDB
from utils import InterviewSession
import os
from config import FILE_DIR

chat = APIRouter(prefix="/chat", tags=["chat"])

@chat.post("/")
async def start_interview(
    token: str = Cookie(None),
    file: UploadFile = None,
    url: str = Form(None),
    db: Session = Depends(get_db)
):
    if not token:
        return {"message": "토큰이 필요합니다."}
    
    pdf_path = None
    if file:
        pdf_path = os.path.join(FILE_DIR, f"{token}.pdf")
        with open(pdf_path, "wb") as buffer:
            buffer.write(file.file.read())
    
    session = db.query(InterviewSessionDB).filter_by(session_token=token).first()
    if not session:
        session = InterviewSessionDB(session_token=token)
        db.add(session)
        db.commit()
    
    # 메인 질문 생성
    interview = InterviewSession(token, pdf_path=pdf_path, url=url, db=db)
    main_question = await interview.generate_main_question()
    
    new_main_question = MainQuestionDB(session_id=session.id, content=main_question)
    db.add(new_main_question)
    db.commit()
    
    return {"type": "main", "question": main_question}

@chat.post("/q")
async def handle_answer(answer: str = Form(...), token: str = Cookie(None), db: Session = Depends(get_db)):
    if not token:
        return {"message": "토큰이 필요합니다."}
    
    session = db.query(InterviewSessionDB).filter_by(session_token=token).first()
    if not session:
        return {"message": "세션이 존재하지 않습니다."}
    
    main_question = db.query(MainQuestionDB)\
        .filter_by(session_id=session.id)\
        .order_by(MainQuestionDB.id.desc()).first()
    if not main_question:
        return {"message": "대표질문이 존재하지 않습니다."}
    
    interview = InterviewSession(token, db=db)
    follow_up_question = await interview.generate_follow_up(answer)
    hint = await interview.generate_hint(follow_up_question)
    feedback, clarity_score, relevance_score = await interview.generate_feedback(answer)
    
    new_follow_up = FollowUpDB(
        main_question_id=main_question.id,
        session_id=session.id,
        content=follow_up_question,
        answer=answer,
        hint=hint,
        feedback=feedback,
        clarity_score=clarity_score,
        relevance_score=relevance_score
    )
    db.add(new_follow_up)
    db.commit()
    
    chat_log = ChatLogDB(
        session_id=session.id,
        question_id=new_follow_up.id,
        user_message=answer,
        system_response=follow_up_question
    )
    db.add(chat_log)
    db.commit()
    
    return {
        "type": "follow_up",
        "question": follow_up_question,
        "hint": hint,
        "feedback": feedback,
        "scores": {
            "clarity": clarity_score,
            "relevance": relevance_score
        }
    }

@chat.post("/end_session")
async def end_session(token: str = Cookie(None), db: Session = Depends(get_db)):
    if not token:
        return {"message": "토큰이 필요합니다."}
    
    session = db.query(InterviewSessionDB).filter_by(session_token=token).first()
    if not session:
        return {"message": "세션이 존재하지 않습니다."}
    
    session.ended = True
    db.commit()
    
    return {"message": "세션이 종료되었습니다."}

@chat.get("/history")
async def get_chat_history(token: str = Cookie(None), db: Session = Depends(get_db)):
    """
    특정 세션 토큰의 채팅 로그를 조회
    """
    if not token:
        return {"message": "토큰이 필요합니다."}
    
    session = db.query(InterviewSessionDB).filter_by(session_token=token).first()
    if not session:
        return {"message": "세션이 존재하지 않습니다."}
    
    chat_logs = db.query(ChatLogDB)\
        .filter_by(session_id=session.id)\
        .order_by(ChatLogDB.timestamp)\
        .all()
    
    history = [
        {
            "timestamp": log.timestamp,
            "user_message": log.user_message,
            "system_response": log.system_response
        }
        for log in chat_logs
    ]
    
    return {"history": history}

@chat.get("/ended_sessions")
async def get_ended_sessions(db: Session = Depends(get_db)):
    """
    종료된(ended=True) 세션 목록 반환
    """
    ended_sessions = db.query(InterviewSessionDB).filter_by(ended=True).all()
    # 필요에 맞게 데이터 변환
    results = []
    for s in ended_sessions:
        results.append({
            "id": s.id,
            "session_token": s.session_token,
            "created_at": s.created_at,  # DB에 필드가 있다면
            "updated_at": s.updated_at,  # DB에 필드가 있다면
        })
    return {"sessions": results}
