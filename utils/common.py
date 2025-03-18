import os, sys
sys.path.append(os.path.dirname(os.path.abspath(os.path.dirname(__file__))))

from fastapi import HTTPException
from config import FILE_DIR
import pandas as pd
from PyPDF2 import PdfReader
from config import API_KEY
import openai
import re

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

# 이력서(PDF)에서 텍스트 추출하는 함수
def load_pdf_to_text(pdf_path):
    text = ""
    reader = PdfReader(pdf_path)
    for page in reader.pages:
        text += page.extract_text()
    return text

# 추출한 텍스트 요약하는 함수
def summarize_text(text, max_length=1000):
    client = openai.OpenAI(api_key=api_key)
    response = client.chat.completions.create(  # ✅ 최신 API 방식
        model="gpt-4-turbo-preview",  # 가장 최신 GPT-4 모델 사용
        messages=[
            {"role": "system", "content": "You are a helpful and smart assistant."},
            {"role": "user", "content": f"Summarize this text in korean: {text}"}
        ],
        max_tokens=max_length
    )
    summary = response.choices[0].message.content  # ✅ 최신 방식
    return summary

# CSV 파일에서 모의 면접 데이터 읽기 (프롬프트 예시를 위해)
def load_mock_interview_data(csv_path, num_examples=2):
    csv_path = "/Users/jeongsu-in/JOBS-Server-2/data/jobkorea.csv"
    df = pd.read_csv(csv_path)
    sample_data = df.sample(n=num_examples)
    examples = [
        f"질문: {row['question']} 답변: {row['answer']}"
        for _, row in sample_data.iterrows()
    ]
    return examples

def extract_video_id(youtube_url):
    # 다양한 유튜브 URL 패턴 대응
    patterns = [
        r"v=([a-zA-Z0-9_-]+)",  # 일반적인 URL (//https:www.youtube.com/watch?v=영상ID)
        r"youtu\.be/([a-zA-Z0-9_-]+)",  # 단축 URL (https://youtu.be/영상ID)
        r"embed/([a-zA-Z0-9_-]+)"  # 임베드 URL (https://www.youtube.com/embed/영상ID)
    ]
    for pattern in patterns:
        match = re.search(pattern, youtube_url)
        if match:
            return match.group(1)  # video_id 추출

    return "유효한 유튜브 링크가 아닙니다."

# 테스트
# youtube_url = "https://youtu.be/iZDQzbKUy3M?si=yaCp1Ybv8TSUMPJa"
rink = "https://youtu.be/4ry9mBEgNA4?si=hmnHqxZmNXSU35r5"
video_id = extract_video_id(rink)
print(f"Extracted video_id: {video_id}")  # 기대 결과: iZDQzbKUy3M
