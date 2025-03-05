import os
import json
import faiss
import numpy as np
import whisper
import yt_dlp
import pandas as pd
from sentence_transformers import SentenceTransformer
# from pymongo import MongoClient
from routers.pdf_storage import pdf_files  # ✅ pdf_files를 직접 불러오도록 변경

# 현재 파일의 경로를 기준으로 youtube_data.json 파일 경로 설정
YOUTUBE_DATA_PATH = os.path.join(os.path.dirname(__file__), "youtube_data.json")

# json 파일 로드
try:
    with open(YOUTUBE_DATA_PATH, "r") as f:
        youtube_data = json.load(f)
except FileNotFoundError:
    raise FileNotFoundError(f"❌ ERROR: '{YOUTUBE_DATA_PATH}' 파일을 찾을 수 없습니다.")

# 비디오 오디오 추출
def save_video_audio(url, filename):
        ydl_opts = {
            'format': 'bestaudio/best',
            'outtmpl': filename,
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }]
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])

# 음성에서 텍스트 추출
def extract_video_text(audio_file):
        model = whisper.load_model("large")
        result = model.transcribe(audio_file)
        return result["text"]

for video in youtube_data:
        filename = f"{video['video_id']}.mp3"
        save_video_audio(video["url"], filename)  # 오디오 다운로드
        text = extract_video_text(filename)  # 텍스트 변환
        video["text"] = text  # 영상 내용 저장 -> 딕셔너리에 추가됌
        # youtube_data.append(video)

# 추출한 텍스트 -> 벡터 DB
model = SentenceTransformer('all-MiniLM-L6-v2')
video_texts = [video["text"] for video in youtube_data]  # 변환된 텍스트 리스트
embeddings = model.encode(video_texts, convert_to_numpy=True)  # 벡터화

# FAISS 벡터 데이터베이스 생성 및 삽입
d = embeddings.shape[1]
index = faiss.IndexFlatL2(d)
index.add(embeddings)

# 이력서 기반 영상 추천 시스템
class RecommendVideo:
    def __init__(self, token: str, video_database: pd.DataFrame, top_n=6):
        self.token = token 
        self.video_database = video_database
        self.top_n = top_n
        self.resume_text = self._get_resume_text() # 이력서 가져오기
        self.resume_vector = model.encode([self.resume_text], convert_to_numpy=True)
    
    # 토큰별로 저장해놨던 resume_text 가져오기
    def _get_resume_text(self):
        if self.token not in pdf_files:
            print(f"❌ [ERROR] Token '{self.token}' not found in pdf_files")
            return ""
        return pdf_files[self.token].get("resume_text", "")
    
    # 이력서 기반 추천해주는 함수
    def recommend_videos(self):
        if not self.resume_text:
            print("❌ No resume text found. Cannot perform recommendation.")
            return []
        
        D, I = index.search(self.resume_vector, self.top_n)
        recommendations = [youtube_data[i] for i in I[0]]
        return recommendations

# 실행
'''if __name__ == "__main__":
    # 이력서 기반 추천 실행
    recommender = RecommendVideo("Ari Kim")  # ✅ 이력서 내용 가져오기
    recommended_videos = recommender.recommend_videos()

    print("Recommended Videos based on Resume:")
    for video in recommended_videos:
        print(video["title"], "-", video["url"])'''
