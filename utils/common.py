import os, sys
sys.path.append(os.path.dirname(os.path.abspath(os.path.dirname(__file__))))

from fastapi import HTTPException
from config import FILE_DIR
import pandas as pd
from PyPDF2 import PdfReader

# 오류 발생 시 오류 출력되도록 (부가기능임)
def echo(status_code: int = None, detail = None) -> any:
    if status_code != None:
        detail = HTTPException(status_code, detail)
    print(detail)
    return detail

# 서버 종료 시 파일에 저장된 이력서 등 다 삭제 -> 초기화 
def clean_files():
    print("Clean files started")
    if os.path.exists(FILE_DIR):
        for f in os.scandir(FILE_DIR):
            os.remove(f.path)
    print("Clean files completed")

# PDF에서 텍스트를 불러오는 함수: fitz -> PyPDF2로 모듈 변경
def load_pdf_to_text(pdf_path):
    text = ""
    reader = PdfReader(pdf_path)
    for page in reader.pages:
        text += page.extract_text()
    return text

# 텍스트 요약 함수
def summarize_text(text, max_chars=1500):
    """텍스트를 지정된 문자 수로 요약"""
    if len(text) > max_chars:
        return text[:max_chars] + "..."
    return text

# CSV 파일에서 모의 면접 데이터 읽기
def load_mock_interview_data(csv_path, num_examples=2):
    df = pd.read_csv(csv_path)
    sample_data = df.sample(n=num_examples)
    examples = [
        f"질문: {row['question']} 답변: {row['answer']}"
        for _, row in sample_data.iterrows()
    ]
    return examples
