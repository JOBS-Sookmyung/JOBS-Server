import os, sys
sys.path.append(os.path.dirname(os.path.abspath(os.path.dirname(__file__))))

from fastapi import HTTPException
from config import FILE_DIR
import pandas as pd
from PyPDF2 import PdfReader
from config import API_KEY
import openai

api_key = API_KEY

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

# 이력서(PDF)에서 텍스트를 불러오는 함수
def load_pdf_to_text(pdf_path):
    text = ""
    reader = PdfReader(pdf_path)
    for page in reader.pages:
        text += page.extract_text()
    return text

# 텍스트 요약 함수 -> 수정
'''def summarize_text(text, max_chars=1500):
    """텍스트를 지정된 문자 수로 요약"""
    if len(text) > max_chars:
        return text[:max_chars] + "..."
    return text'''

def summarize_text(text, max_length=1000):
    client = openai.OpenAI(api_key=api_key)
    response = client.chat.completions.create(  # ✅ 최신 API 방식
        model="gpt-3.5-turbo",
        messages=[
            {"role": "system", "content": "You are a helpful and smart assistant."},
            {"role": "user", "content": f"Summarize this text in korean: {text}"}
        ],
        max_tokens=max_length
    )
    summary = response.choices[0].message.content  # ✅ 최신 방식
    return summary

# CSV 파일에서 모의 면접 데이터 읽기
def load_mock_interview_data(csv_path, num_examples=2):
    df = pd.read_csv(csv_path)
    sample_data = df.sample(n=num_examples)
    examples = [
        f"질문: {row['question']} 답변: {row['answer']}"
        for _, row in sample_data.iterrows()
    ]
    return examples
