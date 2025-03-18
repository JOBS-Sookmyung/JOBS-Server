import numpy as np
import pandas as pd
from sentence_transformers import SentenceTransformer
import faiss 
# from pymongo import MongoClient
from routers.pdf_storage import pdf_storage
from langchain_community.llms import OpenAI  # 새로운 방식


def load_faiss_index(faiss_path):
    try:
        index = faiss.read_index(faiss_path)
        print(f"✅ FAISS 인덱스 로드 완료: {faiss_path}")
        return index
    except Exception as e:
        print(f"❌ FAISS 인덱스 로드 실패: {str(e)}")
        return None

class RecommendVideo:
    def __init__(self, token: str, video_database: pd.DataFrame, top_n=6):
        self.token = token 
        self.video_database = video_database
        self.top_n = top_n
        
        # pdf_storage에서 이력서 텍스트 가져오기
        pdf_data = pdf_storage.get_pdf(token)
        self.resume_text = pdf_data.get("resume_text", "")
        
        if not self.resume_text:
            print(f"❌ 이력서 텍스트를 찾을 수 없음 (토큰: {token})")
        else:
            print(f"✅ 이력서 텍스트 로드 완료 (길이: {len(self.resume_text)})")
        
        self.model = SentenceTransformer('all-MiniLM-L6-v2')
        
        # 이력서 텍스트 벡터화
        self.resume_vector = self.model.encode([self.resume_text], convert_to_numpy=True)
        
        # FAISS 인덱스 로드
        self.index = load_faiss_index("utils/youtube.faiss")
    
    async def recommend_videos(self):
        if not self.resume_text:
            print("❌ 이력서 텍스트가 없어 추천할 수 없습니다.")
            return []

        try:
            # FAISS 인덱스를 이용한 검색
            D, I = self.index.search(self.resume_vector, self.top_n)
            
            recommendations = []
            for idx in I[0]:
                video_info = self.video_database.iloc[idx]
                recommendations.append({
                    "id": video_info["video_id"],  # YouTube 비디오 ID
                    "title": video_info["title"],
                    "thumbnail": f"https://img.youtube.com/vi/{video_info['video_id']}/maxresdefault.jpg",
                    "url": f"https://www.youtube.com/watch?v={video_info['video_id']}"
                })
            
            print(f"✅ 추천 완료: {len(recommendations)}개 영상")
            return recommendations

        except Exception as e:
            print(f"❌ 추천 처리 중 오류 발생: {str(e)}")
            return []

def get_recommendations(token: str):
    pdf_data = pdf_storage.get_pdf(token)
    if not pdf_data:
        return None
    # 나머지 로직...
