import os, sys
sys.path.append(os.path.dirname(os.path.abspath(os.path.dirname(__file__))))

from fastapi import APIRouter
from fastapi import Response, Cookie
from fastapi import File, Form, UploadFile
# from pydantic import BaseModel
from config import FILE_DIR, MAX_FSIZE
from utils import echo, load_pdf_to_text
import uuid
import pdfplumber

# 파일 목록 초기화
pdf_files = dict()

# input page에서
input = APIRouter(prefix="/input", tags=["input"])


# 개개인별로 토큰 생성 후 생성된 토큰을 불러옴 // 확인용
@input.get("/")
async def reload_form(token: str = Cookie(None)):
    if not token or token not in pdf_files:
        return None
    
    return pdf_files[token]


# 업로드 된 파일과 공고주소를 토큰에 저장함
@input.post("/uploadfile/")
async def upload_file(
    res: Response,
    token: str = Cookie(None),
    file: UploadFile = File(),
    recruitUrl: str = Form(),
    # summaryText: str = Form(),
    recentDate: str = Form()
):
    if not token:
        # 유니크한 토큰 설정
        token = str(uuid.uuid1())
        res.set_cookie("token", token)
    
    content = await file.read()

    fsize = len(content)
    if fsize > MAX_FSIZE: # 50MB
        raise echo(
            status_code=413,
            detail=f"파일 크기가 너무 큽니다. (50MB 제한): 현재 크기 {fsize / (1024 * 1024):.2f} MB"
        )
    
    # 입력받은 pdf 파일을 토큰으로 이름 저장
    fname = f"{token}.pdf"

    # 파일 경로가 있는지 확인 후 없으면 경로 생성
    if not os.path.exists(FILE_DIR):
        os.makedirs(name=FILE_DIR, exist_ok=True)

    # 파일 열고 저장 시도
    try:
        SAVE_DIR = os.path.join(FILE_DIR, fname)
        with open(SAVE_DIR, "wb+") as fsave:
            fsave.write(content)
        
        # PDF 내용 추출 (resume_text 추가)
        try:
            with pdfplumber.open(SAVE_DIR) as pdf:
                resume_text = "".join(page.extract_text() or "" for page in pdf.pages)
        except Exception as e:
            resume_text = "이력서를 가져오는데 실패했습니다."

    # 실패시
    except Exception as e:
        raise echo(status_code=500, detail=str(e))
    
    # 성공시
    else:
        pdf_files[token] = {
            "resume_text" : resume_text, # 추후에 DB 연동하면서 수정될 수 있음
            "recruitUrl": recruitUrl,
            # "summaryText": summaryText,
            "recentDate": recentDate,
        }
        print(pdf_files)
        return {"message": f"Upload file saved successfully: \"{fname}\" to \"{FILE_DIR}\""}
    
    # 파일 닫기
    finally:
        await file.close()

