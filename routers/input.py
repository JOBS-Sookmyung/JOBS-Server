import os
import uuid
from fastapi import APIRouter, Response, Cookie, File, Form, UploadFile, HTTPException
from config import FILE_DIR, MAX_FSIZE
from utils import echo, load_pdf_to_text
from routers.pdf_storage import pdf_files

# Ensure the FILE_DIR exists
if not os.path.exists(FILE_DIR):
    os.makedirs(FILE_DIR, exist_ok=True)

input = APIRouter(prefix="/input", tags=["input"])

# 파일 목록 초기화
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
    file: UploadFile = File(...),
    recruitUrl: str = Form(...),
):
    # Generate unique token if not provided
    if not token:
        token = str(uuid.uuid4())  # Generate a new token
        res.set_cookie("token", token)

    content = await file.read()
    file_size = len(content)

    # File size validation
    if file_size > MAX_FSIZE:
        raise HTTPException(
            status_code=413,
            detail=f"파일 크기가 너무 큽니다. (50MB 제한): 현재 크기 {file_size / (1024 * 1024):.2f} MB",
        )

    # Define file path
    file_path = os.path.join(FILE_DIR, f"{token}.pdf")

    # Save the file
    try:
        with open(file_path, "wb") as fsave:
            fsave.write(content)

        # Extract text from PDF
        resume_text = load_pdf_to_text(file_path)

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"파일 저장 중 오류 발생: {str(e)}")

    finally:
        await file.close()

    # Store data in memory (consider using a database)
    pdf_files[token] = {
        "resume_text": resume_text,
        "recruitUrl": recruitUrl,
    }

    print("저장된 데이터:", pdf_files[token])

    # React에서 처리할 URL 반환 (chat 페이지로 이동)
    return {
        "message": "파일 업로드 성공!",
        "token": token,
        "redirect_url": f"/chat?token={token}"  # 프론트엔드에서 chat.js로 이동하는 URL 반환
    }
