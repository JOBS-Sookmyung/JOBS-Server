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
    pool_size=10,  # 기본값으로 줄임
    max_overflow=20,
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

class InterviewSessionDB(Base):
    __tablename__ = "interview_sessions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String(50), ForeignKey("users.id"))
    session_token = Column(String(36), unique=True, index=True)
    status = Column(String(50), default="in_progress")
    current_main_question_index = Column(Integer, default=0)  # 진행 중인 대표질문
    current_follow_up_index = Column(Integer, default=0)  # 진행 중인 꼬리질문
    created_at = Column(DateTime, default=datetime.utcnow)

    # UserDB와의 관계 설정
    user = relationship("UserDB", back_populates="interview_sessions")

class ChatMessageDB(Base):
    __tablename__ = "chat_messages"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(Integer, ForeignKey("interview_sessions.id"))
    message_type = Column(String(50))  # VARCHAR(50)으로 변경
    content = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # 관계 설정
    session = relationship("InterviewSessionDB", back_populates="messages")

# InterviewSessionDB와 ChatMessageDB 간의 관계 설정
InterviewSessionDB.messages = relationship("ChatMessageDB", back_populates="session", cascade="all, delete-orphan")

# 테이블 생성
def create_tables():
    try:
        print("Creating database tables...")
        Base.metadata.create_all(bind=engine)
        print("Database tables created successfully!")
    except Exception as e:
        print(f"Error creating database tables: {str(e)}")
        raise e
