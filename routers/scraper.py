import requests
from bs4 import BeautifulSoup
from fastapi import APIRouter, HTTPException

router = APIRouter()

@router.get("/scrape-url/")
async def scrape_url(url: str):
    try:
        # URL에 요청을 보내고 HTML 응답 받기
        response = requests.get(url)
        response.raise_for_status()  # 4xx, 5xx 에러 발생 시 예외 발생

        # HTML 내용 파싱
        soup = BeautifulSoup(response.content, "html.parser")

        # 예시: 제목과 본문 텍스트 추출 (HTML 구조에 따라 수정 가능)
        title = soup.title.string if soup.title else "제목 없음"
        body = soup.get_text()

        return {"title": title, "body": body}
    
    except requests.exceptions.RequestException as e:
        raise HTTPException(status_code=400, detail=str(e))
