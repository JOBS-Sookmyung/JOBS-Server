from sqlalchemy import create_engine, Column, Integer, String, Text, ForeignKey, DateTime, Boolean
from sqlalchemy.orm import sessionmaker, relationship
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime
from config import SQL_URL
import logging
import pymysql

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# PyMySQL 사용 설정
pymysql.install_as_MySQLdb()

# SQLAlchemy 엔진 생성
engine = create_engine(
    SQL_URL,
    pool_pre_ping=True,
    pool_size=20,
    max_overflow=30,
    echo=True
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# 유저 테이블
class UserDB(Base):
    __tablename__ = "users"
    id = Column(String(50), primary_key=True)
    pw = Column(String(255), nullable=False)
    name = Column(String(50))
    school = Column(String(50))
    phone = Column(String(50))
    interview_sessions = relationship("InterviewSessionDB", back_populates="user")

# 인터뷰 세션 테이블
class InterviewSessionDB(Base):
    __tablename__ = "sessions"
    id = Column(Integer, primary_key=True)
    user_id = Column(String(50), ForeignKey("users.id"))
    session_token = Column(String(36), unique=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    status = Column(String(20), default="in_progress")  # 진행 중, 완료, 중단
    user = relationship("UserDB", back_populates="interview_sessions")
    main_questions = relationship("MainQuestionDB", back_populates="session", cascade="all, delete-orphan")

# 대표 질문 테이블
class MainQuestionDB(Base):
    __tablename__ = "main_questions"
    id = Column(Integer, primary_key=True)
    session_id = Column(Integer, ForeignKey("sessions.id"))
    content = Column(Text, nullable=False)
    session = relationship("InterviewSessionDB", back_populates="main_questions")
    follow_ups = relationship("FollowUpDB", back_populates="main_question", cascade="all, delete-orphan")

# 꼬리 질문 테이블
class FollowUpDB(Base):
    __tablename__ = "follow_ups"
    id = Column(Integer, primary_key=True)
    main_question_id = Column(Integer, ForeignKey("main_questions.id"))
    content = Column(Text, nullable=False)
    answer = Column(Text, nullable=True)
    hint = Column(Text, nullable=True)
    feedback = Column(Text, nullable=True)
    clarity_score = Column(Integer, nullable=True)
    relevance_score = Column(Integer, nullable=True)
    next_question_id = Column(Integer, ForeignKey("follow_ups.id"), nullable=True)  # 다음 꼬리 질문 연결
    main_question = relationship("MainQuestionDB", back_populates="follow_ups")

# 채팅 로그 테이블
class ChatLogDB(Base):
    __tablename__ = "chat_logs"
    id = Column(Integer, primary_key=True)
    session_id = Column(Integer, ForeignKey("sessions.id"))
    question_id = Column(Integer, ForeignKey("follow_ups.id"), nullable=True)
    timestamp = Column(DateTime, default=datetime.utcnow)
    user_message = Column(Text, nullable=False)
    system_response = Column(Text, nullable=True)
    session = relationship("InterviewSessionDB")

# 테이블 생성
def create_tables():
    try:
        Base.metadata.create_all(bind=engine)
        logger.info("데이터베이스 테이블이 성공적으로 생성되었습니다.")
    except Exception as e:
        logger.error(f"테이블 생성 중 오류 발생: {str(e)}")
        raise
