import numpy as np
import pandas as pd
from sentence_transformers import SentenceTransformer
import faiss 
# from pymongo import MongoClient
from routers.pdf_storage import get_pdf  # pdf_files 대신 get_pdf 함수 사용
import os


def load_faiss_index(faiss_path):
    try:
        # 절대 경로로 변환
        abs_path = os.path.join(os.path.dirname(__file__), faiss_path)
        if not os.path.exists(abs_path):
            print(f"❌ FAISS 인덱스 파일이 존재하지 않습니다: {abs_path}")
            return None
            
        index = faiss.read_index(abs_path)
        print(f"✅ FAISS 인덱스 로드 완료: {abs_path}")
        return index
    except Exception as e:
        print(f"❌ FAISS 인덱스 로드 실패: {str(e)}")
        print(f"❌ 시도한 경로: {abs_path}")
        print(f"❌ 상세 오류: {type(e).__name__}")
        return None

class RecommendVideo:
    def __init__(self, token: str, video_database: pd.DataFrame, top_n=6):
        self.token = token 
        self.video_database = video_database
        self.top_n = top_n
        
        # pdf_storage에서 이력서 텍스트 가져오기
        pdf_data = get_pdf(token)
        self.resume_text = pdf_data.get("resume_text", "")
        
        if not self.resume_text:
            print(f"❌ 이력서 텍스트를 찾을 수 없음 (토큰: {token})")
        else:
            print(f"✅ 이력서 텍스트 로드 완료 (길이: {len(self.resume_text)})")
        
        try:
            self.model = SentenceTransformer('all-MiniLM-L6-v2')
            print("✅ SentenceTransformer 모델 로드 완료")
        except Exception as e:
            print(f"❌ SentenceTransformer 모델 로드 실패: {str(e)}")
            raise e
        
        # 이력서 텍스트 벡터화
        try:
            self.resume_vector = self.model.encode([self.resume_text], convert_to_numpy=True)
            print("✅ 이력서 텍스트 벡터화 완료")
        except Exception as e:
            print(f"❌ 이력서 텍스트 벡터화 실패: {str(e)}")
            raise e
        
        # FAISS 인덱스 로드
        self.index = load_faiss_index("youtube.faiss")
        if self.index is None:
            raise Exception("FAISS 인덱스 로드 실패")
    
    async def recommend_videos(self):
        if not self.resume_text:
            print("❌ 이력서 텍스트가 없어 추천할 수 없습니다.")
            return []

        try:
            if self.index is None:
                print("❌ FAISS 인덱스가 로드되지 않았습니다.")
                return []
                
            # FAISS 인덱스를 이용한 검색
            D, I = self.index.search(self.resume_vector, self.top_n)
            
            recommendations = []
            for idx in I[0]:
                if idx < 0 or idx >= len(self.video_database):
                    print(f"❌ 잘못된 인덱스: {idx}")
                    continue
                    
                video_info = self.video_database.iloc[idx]
                recommendations.append({
                    "id": video_info["video_id"],
                    "title": video_info["title"],
                    "thumbnail": f"https://img.youtube.com/vi/{video_info['video_id']}/maxresdefault.jpg",
                    "url": f"https://www.youtube.com/watch?v={video_info['video_id']}"
                })
            
            print(f"✅ 추천 완료: {len(recommendations)}개 영상")
            return recommendations

        except Exception as e:
            print(f"❌ 추천 처리 중 오류 발생: {str(e)}")
            print(f"❌ 상세 오류: {type(e).__name__}")
            return []
