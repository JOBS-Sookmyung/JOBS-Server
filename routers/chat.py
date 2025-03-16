import os, sys

sys.path.append(os.path.dirname(os.path.abspath(os.path.dirname(__file__))))

from fastapi import APIRouter
from fastapi import Response, Cookie, Form, Depends

# from pydantic import BaseModel
from routers import pdf_files
from db import get_db, InterviewSessionDB, MainQuestionDB, FollowUpDB  # db.py에서 직접 import
from utils import echo, InterviewSession
from sqlalchemy.orm import Session


class TokenManager:
    def __init__(self):
        # self.tokens = []
        pass

    # def add(self, token):
    #    self.tokens.append(token)

    @staticmethod
    def is_valid(token: str) -> bool:
        """토큰 유효성 검사"""
        if not token:
            return False
        return True


# chat page에서 api 정의
chat = APIRouter(prefix="/chat", tags=["chat"])


@chat.get("/")
async def start_interview(token: str = Cookie(None), db: Session = Depends(get_db)):
    if not TokenManager.is_valid(token):
        return {"message": "토큰 검증 오류"}

    # 기존 세션 찾기
    current_session = db.query(InterviewSessionDB).filter_by(session_token=token).first()
    if current_session:
        # 기존 세션의 꼬리질문들 삭제
        main_questions = db.query(MainQuestionDB).filter_by(session_id=current_session.id).all()
        for main_q in main_questions:
            db.query(FollowUpDB).filter_by(main_question_id=main_q.id).delete()
        # 기존 메인 질문들 삭제
        db.query(MainQuestionDB).filter_by(session_id=current_session.id).delete()
        # 기존 세션 삭제
        db.delete(current_session)
        db.commit()

    # 새 세션 생성
    pdf_files[token]["session"] = InterviewSession(token=token)
    session = pdf_files[token]["session"]
    new_session = InterviewSessionDB(session_token=token)
    db.add(new_session)
    db.commit()

    # 첫 대표질문 생성
    first_question = await session.generate_main_question()
    return {
        "type": "main",
        "index": 0,
        "question": first_question,
        "progress": session.get_current_state(),
    }



@chat.post("/q")
async def handle_answer(
    answer: str = Form(),
    token: str = Cookie(None),
    db: Session = Depends(get_db),
):
    if not TokenManager.is_valid(token):
        return {"message": "토큰 검증 오류가 발생하였습니다."}

    if not answer:
        raise echo(400, "답변이 비어있습니다.")
    
    # 세션 존재 여부 확인
    if "session" not in pdf_files[token]:
        raise echo(404, "세션이 존재하지 않습니다. 먼저 /chat/를 호출해주세요.")

    session = pdf_files[token]["session"]
    current_session_db = db.query(InterviewSessionDB).filter_by(session_token=token).first()
    if not current_session_db:
        raise echo(404, "DB 상에서 세션을 찾을 수 없습니다.")

    # 사용자 답변을 채팅 로그에 저장
    log = ChatLogDB(
        session_id=current_session_db.id,
        user_message=answer
    )
    db.add(log)
    db.commit()
    db.refresh(log)

    # 아직 대표질문을 모두 소화하지 않았다면
    if session.current_main < session.question_num:
        # 현재 대표질문 DB 객체
        main_q_db_list = (
            db.query(MainQuestionDB)
            .filter_by(session_id=current_session_db.id)
            .order_by(MainQuestionDB.id)
            .all()
        )
        if len(main_q_db_list) <= session.current_main:
            raise echo(404, "현재 대표질문이 DB에 없습니다.")

        current_main_question = main_q_db_list[session.current_main]

        # 꼬리질문 생성 가능 여부
        if session.current_follow_up < session.answer_per_question - 1:
            # 꼬리질문 생성
            next_q = await session.generate_follow_up(answer)
            session.current_follow_up += 1

            # 생성된 꼬리질문을 DB 저장
            follow_up_db = FollowUpDB(
                main_question_id=current_main_question.id,
                content=next_q
            )
            db.add(follow_up_db)
            db.commit()
            db.refresh(follow_up_db)

            # 채팅 로그에 시스템 응답(꼬리질문) 기록
            log.system_response = next_q
            db.add(log)
            db.commit()

            return {
                "type": "follow_up",
                "main_idx": session.current_main,
                "follow_idx": session.current_follow_up,
                "question": next_q,
                "progress": session.get_current_state(),
            }
        else:
            # 꼬리질문 5개가 모두 끝났으므로 다음 대표질문으로 이동
            session.current_main += 1
            session.current_follow_up = 0

            # 5개의 대표질문을 모두 소화했는지 확인
            if session.current_main >= session.question_num:
                current_session_db.status = "finished"
                db.add(current_session_db)
                db.commit()
                return {"status": "인터뷰가 완료되었습니다."}

            # 다음 대표질문 생성
            next_main_q = await session.generate_main_question()
            if next_main_q is None:
                # 더 이상 질문을 생성하지 못하면 세션 종료
                current_session_db.status = "finished"
                db.add(current_session_db)
                db.commit()
                return {"status": "인터뷰가 완료되었습니다."}

            # 새 대표질문을 DB에 저장
            new_main_question_db = MainQuestionDB(
                session_id=current_session_db.id,
                content=next_main_q
            )
            db.add(new_main_question_db)
            db.commit()
            db.refresh(new_main_question_db)

            # 채팅 로그에 시스템 응답(새 대표질문) 기록
            log.system_response = next_main_q
            db.add(log)
            db.commit()

            return {
                "type": "main",
                "index": session.current_main,
                "question": next_main_q,
                "progress": session.get_current_state(),
            }
    else:
        # 이미 5개 대표질문을 완료한 상태
        current_session_db.status = "finished"
        db.add(current_session_db)
        db.commit()
        return {"status": "인터뷰가 완료되었습니다."}



@chat.get("/hint")
async def get_hint(
    main_idx: int,
    follow_idx: int,
    token: str = Cookie(None),
    db: Session = Depends(get_db),
):
    TokenManager.is_valid(token)
    if "session" not in pdf_files[token]:
        raise echo(404, "세션이 존재하지 않습니다.")
    
    session = pdf_files[token]["session"]
    current_session_db = db.query(InterviewSessionDB).filter_by(session_token=token).first()
    if not current_session_db:
        raise echo(404, "DB 상에서 세션을 찾을 수 없습니다.")

    # main_idx에 해당하는 MainQuestionDB 객체를 찾아 꼬리질문
    main_questions = (
        db.query(MainQuestionDB)
        .filter_by(session_id=current_session_db.id)
        .order_by(MainQuestionDB.id)
        .all()
    )
    if main_idx >= len(main_questions):
        raise echo(404, "해당 메인질문이 없습니다.")

    target_main_question = main_questions[main_idx]
    follow_ups = (
        db.query(FollowUpDB)
        .filter_by(main_question_id=target_main_question.id)
        .order_by(FollowUpDB.id)
        .all()
    )
    if follow_idx >= len(follow_ups):
        raise echo(404, "해당 꼬리질문이 없습니다.")

    target_follow_up = follow_ups[follow_idx]

    # 이미 hint가 DB에 있으면 그대로 사용
    if target_follow_up.hint:
        return {"hint": target_follow_up.hint}

    # 없다면 interview.py에서 생성
    hint_text = await session.generate_hint(target_follow_up.content)
    # DB 저장
    target_follow_up.hint = hint_text
    db.add(target_follow_up)
    db.commit()

    return {"hint": hint_text}


@chat.get("/feedback")
async def get_feedback(
    main_idx: int,
    follow_idx: int,
    token: str = Cookie(None),
    db: Session = Depends(get_db),
):
    TokenManager.is_valid(token)
    if "session" not in pdf_files[token]:
        raise echo(404, "세션이 존재하지 않습니다.")
    
    session = pdf_files[token]["session"]
    current_session_db = db.query(InterviewSessionDB).filter_by(session_token=token).first()
    if not current_session_db:
        raise echo(404, "DB 상에서 세션을 찾을 수 없습니다.")

    main_questions = (
        db.query(MainQuestionDB)
        .filter_by(session_id=current_session_db.id)
        .order_by(MainQuestionDB.id)
        .all()
    )
    if main_idx >= len(main_questions):
        raise echo(404, "해당 메인질문이 없습니다.")

    target_main_question = main_questions[main_idx]
    follow_ups = (
        db.query(FollowUpDB)
        .filter_by(main_question_id=target_main_question.id)
        .order_by(FollowUpDB.id)
        .all()
    )
    if follow_idx >= len(follow_ups):
        raise echo(404, "해당 꼬리질문이 없습니다.")

    target_follow_up = follow_ups[follow_idx]

    # 사용자가 이미 답변을 작성했다고 가정
    if not target_follow_up.answer:
        return {"feedback": "아직 답변이 기록되지 않았습니다."}

    # 이미 feedback이 있다면 그대로 사용
    if target_follow_up.feedback:
        return {
            "feedback": target_follow_up.feedback,
            "score": {
                "clarity": target_follow_up.clarity_score,
                "relevance": target_follow_up.relevance_score
            },
        }

    # 새 피드백 생성
    feedback_text = await session.generate_feedback(target_follow_up.answer)

    # 간단한 예: 점수 추출 로직은 여기서 파싱(예: 임시로 4점씩 넣는다)
    clarity_score = 4
    relevance_score = 4

    target_follow_up.feedback = feedback_text
    target_follow_up.clarity_score = clarity_score
    target_follow_up.relevance_score = relevance_score
    db.add(target_follow_up)
    db.commit()

    return {
        "feedback": feedback_text,
        "score": {
            "clarity": clarity_score,
            "relevance": relevance_score
        },
    }

