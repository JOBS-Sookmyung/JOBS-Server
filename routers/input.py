import os, sys
sys.path.append(os.path.dirname(os.path.abspath(os.path.dirname(__file__))))

from fastapi import APIRouter
from fastapi import Response, Cookie
from fastapi import File, Form, UploadFile
# from pydantic import BaseModel
from config import FILE_DIR, MAX_FSIZE
from utils import echo
import uuid

pdf_files = dict()

input = APIRouter(prefix="/input")

@input.get("/", tags=["input"])
async def reload_form(token: str = Cookie(None)):
    if not token or token not in pdf_files:
        return None
    
    return pdf_files[token]

@input.post("/uploadfile/", tags=["input"])
async def upload_file(
    res: Response,
    token: str = Cookie(None),
    file: UploadFile = File(),
    recruitUrl: str = Form(),
    summaryText: str = Form(),
    recentDate: str = Form()
):
    if not token:
        token = str(uuid.uuid1())
        res.set_cookie("token", token)
    
    content = await file.read()

    fsize = len(content)
    if fsize > MAX_FSIZE: # 50MB
        raise echo(
            status_code=413,
            detail=f"Upload file too large (50MB limited): current size {fsize / (1024 * 1024):.2f}MB"
        )
    
    fname = f"{token}.pdf"

    try:
        SAVE_DIR = os.path.join(FILE_DIR, fname)
        with open(SAVE_DIR, "wb+") as fsave:
            fsave.write(content)
    
    except Exception as e:
        raise echo(status_code=500, detail=str(e))
    
    else:
        pdf_files[token] = {
            "recruitUrl": recruitUrl,
            "summaryText": summaryText,
            "recentDate": recentDate
        }
        print(pdf_files)
        return {"message": f"Upload file saved successfully: \"{fname}\" to \"{FILE_DIR}\""}
    
    finally:
        await file.close()
