import os
from fastapi import APIRouter, HTTPException
from utils.recommendation import get_recommendations
from config import FILE_DIR

recommendations = APIRouter(prefix="/recommend", tags=["recommend"])

@recommendations.get("/{token}")
async def recommend_videos(token: str):
    """
    PDF 이력서를 기반으로 추천 영상을 반환합니다.
    """
    # 토큰을 기반으로 PDF 경로 설정
    pdf_path = os.path.join(FILE_DIR, f"{token}.pdf")

    if not os.path.exists(pdf_path):
        raise HTTPException(status_code=404, detail="Resume file not found")

    # 추천 결과 생성
    recommendations = get_recommendations(pdf_path)
    return recommendations
