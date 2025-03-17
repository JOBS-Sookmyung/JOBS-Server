import httpx
from fastapi import APIRouter, HTTPException
from utils.recommendation import RecommendVideo
from config import FILE_DIR
from routers.pdf_storage import pdf_storage
import pandas as pd
import json
import os
from typing import List
from pydantic import BaseModel

# youtube_data.json 파일 로드
with open("utils/youtube_data.json", "r", encoding="utf-8") as f:
    youtube_data = json.load(f)

# DataFrame으로 변환
video_database = pd.DataFrame(youtube_data)

recommendations = APIRouter(prefix="/recommend", tags=["recommend"])

class RecommendationResponse(BaseModel):
    id: str
    title: str
    thumbnail: str
    url: str

@recommendations.get("/{token}", response_model=List[RecommendationResponse])
async def get_recommendations(token: str):
    try:
        print(f"🔍 추천 시스템 요청 - 토큰: {token}")
        
        # 이력서 데이터 조회
        pdf_data = pdf_storage.get_pdf(token)
        if not pdf_data:
            raise HTTPException(status_code=404, detail=f"이력서를 찾을 수 없습니다. (토큰: {token})")
        
        # 이력서 텍스트 가져오기
        resume_text = pdf_data.get("resume_text", "")
        if not resume_text:
            raise HTTPException(status_code=400, detail="이력서 텍스트가 비어있습니다.")
        
        print(f"📄 이력서 텍스트 길이: {len(resume_text)}")
        
        # 추천 시스템 초기화 및 실행
        recommender = RecommendVideo(token=token, video_database=video_database)
        recommended_videos = await recommender.recommend_videos()
        
        if not recommended_videos:
            raise HTTPException(status_code=404, detail="추천 영상을 찾을 수 없습니다.")
        
        print(f"✅ 추천된 영상 수: {len(recommended_videos)}")
        
        # 추천 결과를 pdf_storage에 저장
        pdf_data["recommendations"] = recommended_videos
        pdf_storage.add_pdf(token, pdf_data)
        
        return recommended_videos
        
    except HTTPException as he:
        print(f"❌ HTTP 에러: {he.detail}")
        raise he
    except Exception as e:
        print(f"❌ 서버 에러: {str(e)}")
        raise HTTPException(status_code=500, detail=f"서버 오류: {str(e)}")