from utils import pdfAnalyzer as pa
from pydantic import BaseModel
from fastapi import FastAPI, File, UploadFile
from fastapi.middleware.cors import CORSMiddleware as cors
import uvicorn

import aiofiles
import json
import os

origins = [
    'http://127.0.0.1',
    'http://127.0.0.1:8080'
]

app = FastAPI()
app.add_middleware(
	cors,
    allow_origins=origins,
	allow_methods=["*"],
    allow_headers=["*"],
)

_host = '127.0.0.1'
_port = 8080
_path = os.getcwd()
_filespath = os.path.join(_path, 'files')

class FileModel(BaseModel):
	file: UploadFile = File(None)

@app.post('/files')
async def get_file_to_json(filename: str):
	return pa.pdf_to_json(filename)

@app.post('/uploadfile')
async def upload_file(uploadFile: FileModel):
	async with aiofiles.open(_filespath, 'wb') as outFile:
		content = await uploadFile.file.read()
		await outFile.write(content)
		
	retval = {"filename": uploadFile.file.filename}
	print(retval)
	return retval

class URL(BaseModel):
	url: str

@app.post('/uploadurl')
def upload_url(data: URL):
	retval = {"url": data.url}
	print(retval)
	return retval

if __name__ == '__main__':
    uvicorn.run("main:app", host=_host, port=_port)
