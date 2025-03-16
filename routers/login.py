from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from db import get_db, UserDB
from pydantic import BaseModel

router = APIRouter()

# 회원가입 시 받을 데이터 형식
class UserCreate(BaseModel):
    id: str
    pw: str
    name: str
    school: str
    phone: str

# 로그인 시 받을 데이터 형식
class UserLogin(BaseModel):
    id: str
    pw: str

@router.post("/signup")
def signup(user: UserCreate, db: Session = Depends(get_db)):
    # FastAPI 콘솔에서 확인 용
    print(f"[signup] 요청 받은 아이디: {user.id}")

    # 이미 같은 아이디가 존재하는지 확인
    exist_user = db.query(UserDB).filter(UserDB.id == user.id).first()
    if exist_user:
        print("[signup] 이미 존재하는 아이디입니다.")
        return {"message": "User already exists"}  # 프론트에서 이 메시지 확인 가능

    # 새로운 유저 생성
    new_user = UserDB(
        id=user.id,
        pw=user.pw,  # 비밀번호 해싱 미적용 (주의)
        name=user.name,
        school=user.school,
        phone=user.phone
    )
    db.add(new_user)
    db.commit()

    print("[signup] 회원가입 성공")
    return {"message": "Signup success"}

@router.post("/login")
def login(user: UserLogin, db: Session = Depends(get_db)):
    print(f"[login] 로그인 시도 아이디: {user.id}")
    # 아이디와 비밀번호가 일치하는지 확인
    exist_user = db.query(UserDB).filter(
        UserDB.id == user.id,
        UserDB.pw == user.pw
    ).first()

    if exist_user:
        print("[login] 로그인 성공")
        return {
            "message": "Login success",
            "user": {
                "id": exist_user.id,
                "name": exist_user.name,
                "school": exist_user.school,
                "phone": exist_user.phone
            }
        }
    else:
        print("[login] 로그인 실패 (아이디 혹은 비밀번호 불일치)")
        return {"message": "Invalid credentials"}
