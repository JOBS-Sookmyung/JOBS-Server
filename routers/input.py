import os
import uuid
from fastapi import APIRouter, Response, Cookie, File, Form, UploadFile, HTTPException
from config import FILE_DIR, MAX_FSIZE
from utils import echo, load_pdf_to_text
from routers.pdf_storage import pdf_files

# ✅ 파일 저장 디렉토리가 없으면 생성
if not os.path.exists(FILE_DIR):
    os.makedirs(FILE_DIR, exist_ok=True)

input = APIRouter(prefix="/input", tags=["input"])

# ✅ 저장된 파일 목록 (세션 대체용)
pdf_files = {}

@input.get("/")
async def reload_form(token: str = Cookie(None)):
    if not token or token not in pdf_files:
        return None
    return pdf_files[token]

@input.post("/uploadfile/")
async def upload_file(
    res: Response,
    token: str = Cookie(None),
    file: UploadFile = File(...),  # ✅ PDF 파일 업로드 필드
    recruitUrl: str = Form(...),  # ✅ URL 입력 필드
):
    if not token:
        token = str(uuid.uuid4())  # ✅ 고유한 token 생성
        res.set_cookie("token", token)  # ✅ 클라이언트 쿠키에 저장

    content = await file.read()
    file_size = len(content)

    # ✅ 파일 크기 제한 (50MB)
    if file_size > MAX_FSIZE:
        raise HTTPException(
            status_code=413,
            detail=f"파일 크기가 너무 큽니다. (50MB 제한): 현재 크기 {file_size / (1024 * 1024):.2f} MB",
        )

    file_path = os.path.join(FILE_DIR, f"{token}.pdf")  # ✅ 고유한 파일 이름 설정

    try:
        with open(file_path, "wb") as fsave:
            fsave.write(content)  # ✅ 파일 저장

        resume_text = load_pdf_to_text(file_path)  # ✅ PDF에서 텍스트 추출

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"파일 저장 중 오류 발생: {str(e)}")

    finally:
        await file.close()

    # ✅ 파일 및 URL을 메모리에 저장 (DB 대체 가능)
    pdf_files[token] = {
        "resume_text": resume_text,
        "recruitUrl": recruitUrl,
    }

    print("저장된 데이터:", pdf_files[token])  # ✅ 콘솔 로그 출력

    return {"message": "파일 업로드 성공!", "token": token}  # ✅ React에 JSON 응답 반환
