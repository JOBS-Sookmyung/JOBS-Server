import httpx
from fastapi import APIRouter, HTTPException
from utils.recommendation import get_recommendations
from config import FILE_DIR
from input import pdf_files

recommendations = APIRouter(prefix="/recommend", tags=["recommend"])

# subhome 엔드포인트 URL 설정
SUBHOME_URL = "http://localhost:8000/subhome"  # subhome의 URL

@recommendations.get("/{token}")
async def recommend_videos(token: str):
    if token not in pdf_files:
        raise HTTPException(status_code=404, detail="Resume not found")
    
    resume_text = pdf_files[token].get("resume_text")
    if not resume_text:
        raise HTTPException(status_code=404, detail="Resume content not found")

    # 추천 시스템 호출
    recommendations_data = get_recommendations(resume_text)

    # subhome으로 결과를 전달하는 부분
    try:
        async with httpx.AsyncClient() as client:
            # subhome에 POST 요청을 보냄
            response = await client.post(SUBHOME_URL, json=recommendations_data)
            response.raise_for_status()  # HTTP 오류 발생 시 예외를 발생시킴
            # subhome에서 반환된 응답을 확인
            print("subhome 응답:", response.json())
    except httpx.HTTPStatusError as e:
        raise HTTPException(status_code=e.response.status_code, detail="Subhome 오류")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Subhome 요청 실패: {str(e)}")

    return recommendations_data
