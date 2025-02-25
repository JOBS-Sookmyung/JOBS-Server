import json
import faiss
import numpy as np
import whisper
import yt_dlp
import pandas as pd
from sentence_transformers import SentenceTransformer
from pymongo import MongoClient
from routers.input import pdf_files

youtube_data = [
    {"id": 1, "title": "14년차 UX/UI 디자이너가 말하는 절대 피해야하는 탈락각 포트폴리오", "url": "https://youtu.be/uYjXlhrHr_4?si=yoquZuSIMKibBA5c", "video_id": "uYjXlhrHr_4"},
    {"id": 2, "title": "Machine Learning Basics", "url": "https://youtu.be/abc456", "video_id": "abc456"},
    {"id": 3, "title": "Introduction to MongoDB", "url": "https://youtu.be/mongo789", "video_id": "mongo789"},
    {"id": 4, "title": "Introduction to MongoDB", "url": "https://youtu.be/mongo789", "video_id": "mongo789"},
    {"id": 5, "title": "Introduction to MongoDB", "url": "https://youtu.be/mongo789", "video_id": "mongo789"},
    {"id": 6, "title": "Introduction to MongoDB", "url": "https://youtu.be/mongo789", "video_id": "mongo789"},
    {"id": 7, "title": "Introduction to MongoDB", "url": "https://youtu.be/mongo789", "video_id": "mongo789"},
    {"id": 8, "title": "Introduction to MongoDB", "url": "https://youtu.be/mongo789", "video_id": "mongo789"},
    {"id": 9, "title": "Introduction to MongoDB", "url": "https://youtu.be/mongo789", "video_id": "mongo789"},
    {"id": 10, "title": "Introduction to MongoDB", "url": "https://youtu.be/mongo789", "video_id": "mongo789"},
    {"id": 11, "title": "Introduction to MongoDB", "url": "https://youtu.be/mongo789", "video_id": "mongo789"},
    {"id": 12, "title": "Introduction to MongoDB", "url": "https://youtu.be/mongo789", "video_id": "mongo789"},
    {"id": 13, "title": "Introduction to MongoDB", "url": "https://youtu.be/mongo789", "video_id": "mongo789"},
    {"id": 14, "title": "Introduction to MongoDB", "url": "https://youtu.be/mongo789", "video_id": "mongo789"},
    {"id": 15, "title": "Introduction to MongoDB", "url": "https://youtu.be/mongo789", "video_id": "mongo789"},
    {"id": 16, "title": "Introduction to MongoDB", "url": "https://youtu.be/mongo789", "video_id": "mongo789"},
    {"id": 17, "title": "Introduction to MongoDB", "url": "https://youtu.be/mongo789", "video_id": "mongo789"},
    {"id": 18, "title": "Introduction to MongoDB", "url": "https://youtu.be/mongo789", "video_id": "mongo789"},
    {"id": 19, "title": "Introduction to MongoDB", "url": "https://youtu.be/mongo789", "video_id": "mongo789"},
    {"id": 20, "title": "Introduction to MongoDB", "url": "https://youtu.be/mongo789", "video_id": "mongo789"},
    {"id": 21, "title": "Introduction to MongoDB", "url": "https://youtu.be/mongo789", "video_id": "mongo789"},
    {"id": 22, "title": "Introduction to MongoDB", "url": "https://youtu.be/mongo789", "video_id": "mongo789"},
    {"id": 23, "title": "Introduction to MongoDB", "url": "https://youtu.be/mongo789", "video_id": "mongo789"},
    {"id": 24, "title": "Introduction to MongoDB", "url": "https://youtu.be/mongo789", "video_id": "mongo789"},
    {"id": 25, "title": "Introduction to MongoDB", "url": "https://youtu.be/mongo789", "video_id": "mongo789"},
    {"id": 26, "title": "Introduction to MongoDB", "url": "https://youtu.be/mongo789", "video_id": "mongo789"},
    {"id": 27, "title": "Introduction to MongoDB", "url": "https://youtu.be/mongo789", "video_id": "mongo789"},
    {"id": 28, "title": "Introduction to MongoDB", "url": "https://youtu.be/mongo789", "video_id": "mongo789"},
    {"id": 29, "title": "Introduction to MongoDB", "url": "https://youtu.be/mongo789", "video_id": "mongo789"},
    {"id": 30, "title": "Introduction to MongoDB", "url": "https://youtu.be/mongo789", "video_id": "mongo789"},
    {"id": 31, "title": "Introduction to MongoDB", "url": "https://youtu.be/mongo789", "video_id": "mongo789"},
    {"id": 32, "title": "Introduction to MongoDB", "url": "https://youtu.be/mongo789", "video_id": "mongo789"},
    {"id": 33, "title": "Introduction to MongoDB", "url": "https://youtu.be/mongo789", "video_id": "mongo789"},
    {"id": 34, "title": "Introduction to MongoDB", "url": "https://youtu.be/mongo789", "video_id": "mongo789"},
    {"id": 35, "title": "Introduction to MongoDB", "url": "https://youtu.be/mongo789", "video_id": "mongo789"},
    {"id": 36, "title": "Introduction to MongoDB", "url": "https://youtu.be/mongo789", "video_id": "mongo789"},
    {"id": 37, "title": "Introduction to MongoDB", "url": "https://youtu.be/mongo789", "video_id": "mongo789"},
    {"id": 38, "title": "Introduction to MongoDB", "url": "https://youtu.be/mongo789", "video_id": "mongo789"},
    {"id": 39, "title": "Introduction to MongoDB", "url": "https://youtu.be/mongo789", "video_id": "mongo789"},
    {"id": 40, "title": "Introduction to MongoDB", "url": "https://youtu.be/mongo789", "video_id": "mongo789"},
    {"id": 41, "title": "Introduction to MongoDB", "url": "https://youtu.be/mongo789", "video_id": "mongo789"},
    {"id": 42, "title": "Introduction to MongoDB", "url": "https://youtu.be/mongo789", "video_id": "mongo789"},
    {"id": 43, "title": "Introduction to MongoDB", "url": "https://youtu.be/mongo789", "video_id": "mongo789"},
    {"id": 44, "title": "Introduction to MongoDB", "url": "https://youtu.be/mongo789", "video_id": "mongo789"},
    {"id": 45, "title": "Introduction to MongoDB", "url": "https://youtu.be/mongo789", "video_id": "mongo789"},
    {"id": 46, "title": "Introduction to MongoDB", "url": "https://youtu.be/mongo789", "video_id": "mongo789"},
    {"id": 47, "title": "Introduction to MongoDB", "url": "https://youtu.be/mongo789", "video_id": "mongo789"},
    {"id": 48, "title": "Introduction to MongoDB", "url": "https://youtu.be/mongo789", "video_id": "mongo789"},
    {"id": 49, "title": "Introduction to MongoDB", "url": "https://youtu.be/mongo789", "video_id": "mongo789"},
    {"id": 50, "title": "Introduction to MongoDB", "url": "https://youtu.be/mongo789", "video_id": "mongo789"},
    {"id": 51, "title": "Introduction to MongoDB", "url": "https://youtu.be/mongo789", "video_id": "mongo789"},
    {"id": 52, "title": "Introduction to MongoDB", "url": "https://youtu.be/mongo789", "video_id": "mongo789"}
]

with open("youtube_data.json", "w") as f:
        json.dump(youtube_data, f, indent=4)

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

def search_videos(query, top_k=3):
        """ 사용자가 입력한 검색어와 가장 유사한 영상을 추천 """
        query_embedding = model.encode([query], convert_to_numpy=True)  # 검색어 벡터화
        D, I = index.search(query_embedding, top_k)  # FAISS 검색
        results = [youtube_data[i] for i in I[0]]  # 검색된 영상 반환
        return results

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
if __name__ == "__main__":
    # 이력서 기반 추천 실행
    recommender = RecommendVideo("Ari Kim")  # ✅ 이력서 내용 가져오기
    recommended_videos = recommender.recommend_videos()

    print("Recommended Videos based on Resume:")
    for video in recommended_videos:
        print(video["title"], "-", video["url"])
