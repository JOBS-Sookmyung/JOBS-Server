from sqlalchemy import create_engine
from sqlalchemy import Column, Integer, String, Text, ForeignKey
from sqlalchemy.orm import sessionmaker, relationship
from sqlalchemy.ext.declarative import declarative_base
from config import SQL_URL

# SQLAlchemy 엔진 생성
engine = create_engine(
    SQL_URL,
    pool_pre_ping=True,  # 커넥션 풀 건강 상태 검사
    pool_size=20,  # 기본 커넥션 풀 크기
    max_overflow=30,  # 최대 오버플로우 커넥션
)

# 세션 팩토리 생성
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# 모델 베이스 클래스
Base = declarative_base()

# Dependency 생성
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# 테이블 생성 함수 (앱 시작 시 실행)
def create_tables(): 
    Base.metadata.create_all(bind=engine)
    
# 유저 테이블 모델
class UserDB(Base):
    __tablename__ = "users"
    id = Column(String(50), primary_key=True)       # 아이디
    pw = Column(String(255), nullable=False)        # 비밀번호
    name = Column(String(50))                       # 이름
    school = Column(String(50))                     # 학교
    phone = Column(String(50))                      # 전화번호

# 인터뷰 세션 테이블 모델
class InterviewSessionDB(Base):
    __tablename__ = "sessions"
    id = Column(Integer, primary_key=True)
    token = Column(String(36), unique=True)
    main_questions = relationship("MainQuestionDB", back_populates="session")

# 대표질문 테이블 모델
class MainQuestionDB(Base):
    __tablename__ = "main_questions"
    id = Column(Integer, primary_key=True)
    content = Column(Text)
    session_id = Column(Integer, ForeignKey("sessions.id"))
    session = relationship("InterviewSessionDB", back_populates="main_questions")
    follow_ups = relationship("FollowUpDB", back_populates="main_question")

# 꼬리질문 테이블 모델
class FollowUpDB(Base):
    __tablename__ = "follow_ups"
    id = Column(Integer, primary_key=True)
    content = Column(Text)
    answer = Column(Text)
    main_question_id = Column(Integer, ForeignKey("main_questions.id"))
    main_question = relationship("MainQuestionDB", back_populates="follow_ups")
