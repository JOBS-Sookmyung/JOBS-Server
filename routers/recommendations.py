import os
from fastapi import APIRouter, HTTPException
from utils.recommendation import get_recommendations
from config import FILE_DIR
from input import pdf_files

recommendations = APIRouter(prefix="/recommend", tags=["recommend"])

@recommendations.get("/{token}")
async def recommend_videos(token: str):
    if token not in pdf_files:
        raise HTTPException(status_code=404, detail="Resume not found")
    
    resume_text = pdf_files[token].get("resume_text")
    if not resume_text:
        raise HTTPException(status_code=404, detail="Resume content not found")

    recommendations = get_recommendations(resume_text)
    return recommendations
