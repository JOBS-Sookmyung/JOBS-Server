import numpy as np
import pandas as pd
from sentence_transformers import SentenceTransformer
# from pymongo import MongoClient
from routers.pdf_storage import pdf_files  # ✅ pdf_files를 직접 불러오도록 변경
from utils.extract_video import load_faiss_index

class RecommendVideo:
    def __init__(self, token: str, video_database: pd.DataFrame, top_n=6):
        self.token = token 
        self.video_database = video_database
        self.top_n = top_n
        self.resume_text = self._get_resume_text()  # 이력서 텍스트 가져오기
        self.model = SentenceTransformer('all-MiniLM-L6-v2')
        
        # 이력서 텍스트 벡터화
        self.resume_vector = self.model.encode([self.resume_text], convert_to_numpy=True)
        
        # FAISS 인덱스 로드
        self.index = load_faiss_index("video_index.faiss")
    
    def _get_resume_text(self):
        # 이력서 텍스트 반환
        if self.token not in pdf_files:  # pdf_files는 이력서 텍스트를 가지고 있는 곳
            print(f"❌ [ERROR] Token '{self.token}' not found in pdf_files")
            return ""
        return pdf_files[self.token].get("resume_text", "")

    async def recommend_videos(self):
        if not self.resume_text:
            print("❌ No resume text found. Cannot perform recommendation.")
            return []

        # FAISS 인덱스를 이용한 검색
        D, I = self.index.search(self.resume_vector, self.top_n)
        
        # 추천 영상 리스트
        recommendations = [self.video_database.iloc[i] for i in I[0]]  
        return recommendations
