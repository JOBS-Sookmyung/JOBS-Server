# pip install openai-whisper, openai, spacy, yt-dlp, youtube-dl, pafy, google.colab
# brew install ffmpeg -> bash 셀에서 해야함 (pip으로 하면 안됌, 하단 부분 터미널 주의(zsh 말고 bash)
import os
import pandas as pd
import whisper
import openai, spacy, yt_dlp
from IPython.display import Audio
from spacy.lang.ko.examples import sentences
import pafy
from langchain.prompts import PromptTemplate
from langchain.chains import LLMChain
from langchain.llms import OpenAI
from config import FILE_DIR, API_KEY, PAFY_KEY
from utils.common import load_pdf_to_text, summarize_text, safe_video, extract_video_text, vectorize_text, find_similar_videos

pafy_key = PAFY_KEY
api_key = API_KEY
pafy.set_api_key(PAFY_KEY)

# 비디오 mp3로 저장
def safe_video(self):
    url = "https://www.youtube.com/watch?v=vjiUBshORo8"
    ydl_opts = {
        'format': 'bestaudio/best',  # 최고 품질 오디오 선택
        'outtmpl': 'hyundaimobis.mp3',  # 파일명 지정
        'postprocessors': [{  # MP3로 변환
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',  # 음질 설정 (128, 192, 320kbps)
        }],
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([url])

# mp3에서 텍스트 추출
def extract_video_text(self):
    model = whisper.load_model("large") # Large 모델 불러오기
    result = model.transcribe("hyundaimobis.mp3") # MP3 파일에서 추출
    output = result["text"] # 추출된 텍스트 출력
    print(output)

class RecommendVideo:
    """
    사용자의 이력서를 기반으로 유사한 유튜브 영상을 추천하는 시스템.
    """
    def __init__(self, token: str, video_database: pd.DataFrame, top_n=6):
        self.token = token 
        self.video_database = video_database
        self.top_n = top_n
        self.resume_text = self._extract_resume_text(token) # token 값을 입력하면 자동으로 해당 토큰의 PDF 불러오기
        self.resume_vector = vectorize_text(self.resume_text)
    
    def _extract_resume_text(self):
        """사용자가 입력한 이력서에서 텍스트를 추출."""
        if not os.path.exists(self.resume_path):
            raise FileNotFoundError("해당 경로에 이력서 파일이 존재하지 않습니다.")
        resume_text = load_pdf_to_text(self.resume_path)
        return summarize_text(resume_text, max_length=1500)
    
    def recommend_videos(self):
        """유사도가 높은 유튜브 영상 추천."""
        video_vectors = self.video_database['transcript'].apply(vectorize_text)
        recommendations = find_similar_videos(self.resume_vector, video_vectors, self.top_n)
        return self.video_database.iloc[recommendations]
    
if __name__ == "__main__":
    video_database_df = pd.read_csv("video_database.csv")  # 예제 영상 데이터
    resume_file_path = "user_resume.pdf"
    recommender = RecommendVideo(resume_file_path, video_database_df)
    recommended_videos = recommender.recommend_videos()
    print(recommended_videos)
