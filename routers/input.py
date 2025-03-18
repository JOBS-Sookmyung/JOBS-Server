import os
import uuid
from fastapi import APIRouter, Response, Cookie, File, Form, UploadFile, HTTPException
from config import FILE_DIR, MAX_FSIZE
from utils import echo, load_pdf_to_text
from routers.pdf_storage import pdf_storage
from datetime import datetime

# Ensure the FILE_DIR exists
if not os.path.exists(FILE_DIR):
    os.makedirs(FILE_DIR, exist_ok=True)

input = APIRouter(prefix="/input", tags=["input"])

@input.get("/")
async def reload_form(token: str = Cookie(None)):
    if not token:
        return None
    pdf_data = pdf_storage.get_pdf(token)
    if not pdf_data:
        return None
    return pdf_data

@input.post("/uploadfile/")
async def upload_file(
    res: Response,
    file: UploadFile = File(...),
    recruitUrl: str = Form(...),
):
    # 항상 새로운 토큰 생성
    token = str(uuid.uuid4())
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

    # Store data in memory using pdf_storage
    pdf_data = {
        "resume_text": resume_text,
        "recruitUrl": recruitUrl,
        "created_at": datetime.now().isoformat(),  # 생성 시간 추가
    }
    pdf_storage.add_pdf(token, pdf_data)

    print(f"✅ 파일 업로드 완료 - 토큰: {token}")
    
    return {
        "message": "파일 업로드 성공!",
        "token": token,
        "redirect_url": f"/chat?token={token}"
    }

@input.get("/pdf/{token}")
async def get_pdf(token: str):
    if not token:
        raise HTTPException(status_code=400, detail="토큰이 필요합니다.")
    
    pdf_data = pdf_storage.get_pdf(token)
    if not pdf_data:
        raise HTTPException(status_code=404, detail="PDF를 찾을 수 없습니다.")
    
    return pdf_data
