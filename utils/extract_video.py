import os
import json
import yt_dlp
import whisper
from sentence_transformers import SentenceTransformer
import asyncio
import faiss

# youtube_data.json 경로 설정
YOUTUBE_DATA_PATH = os.path.join(os.path.dirname(__file__), "youtube_data.json")

# 오디오 다운로드 경로 설정 (절대 경로 사용)
output_dir = os.path.join(os.path.dirname(__file__), "downloads")
os.makedirs(output_dir, exist_ok=True)
# filename = os.path.join(output_dir, f"{video['video_id']}")

# json 파일 로드
try:
    with open(YOUTUBE_DATA_PATH, "r") as f:
        youtube_data = json.load(f)
except FileNotFoundError:
    raise FileNotFoundError(f"❌ ERROR: '{YOUTUBE_DATA_PATH}' 파일을 찾을 수 없습니다.")

# whisper 모델 로드 (한 번만 로딩)
model = whisper.load_model("small")

# 비디오 오디오 추출 (비동기 처리)
async def save_video_audio(url, filename):
    ydl_opts = {
        'format': 'bestaudio/best',
        'outtmpl': filename,  # 오디오 다운로드 파일 이름 지정
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',
        }],
        'postprocessor_args': ['-vn'],  # 비디오 비활성화 (오디오만)
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        await asyncio.to_thread(ydl.download, [url])  # 비동기로 다운로드

    # 후처리된 파일 이름을 '.mp3'로 변경
    if filename.endswith(".mp3.mp3"):
        os.rename(f"{filename}.mp3", f"{filename}.mp3")  # 중복된 .mp3 제거
    elif not filename.endswith(".mp3"):
        os.rename(filename, f"{filename}.mp3")  # 확장자 없는 경우 .mp3로 변경


# 음성에서 텍스트 추출
async def extract_video_text(audio_file):
    result = await asyncio.to_thread(model.transcribe, audio_file)  # 비동기 텍스트 추출
    print(result['text'])
    return result["text"]


async def process_videos():
    for video in youtube_data:
        filename = os.path.join(output_dir, f"{video['video_id']}.mp3")  # 확장자 추가
        await save_video_audio(video["url"], filename)  # 오디오 다운로드
        
        # 디버깅 출력 추가
        print(f"저장된 파일 경로: {filename}")
        
        if os.path.exists(filename):  # 파일이 존재하는지 확인
            text = await extract_video_text(filename)  # 텍스트 변환
            video["text"] = text  # 영상 내용 저장 -> 딕셔너리에 추가
        else:
            print(f"❌ {filename} 파일을 찾을 수 없습니다.")

# 비디오 텍스트 -> 벡터 DB
async def vectorize_and_save():
    print("2번째 함수 시작 개 큰 시작")
    model = SentenceTransformer('all-MiniLM-L6-v2')
    video_texts = [video["text"] for video in youtube_data]  # 변환된 텍스트 리스트
    embeddings = model.encode(video_texts, convert_to_numpy=True)  # 벡터화

    # FAISS 벡터 데이터베이스 생성 및 삽입
    d = embeddings.shape[1]
    index = faiss.IndexFlatL2(d)
    index.add(embeddings)
    
    # FAISS 인덱스를 파일로 저장 (추후 서버에서 불러올 수 있도록)
    faiss.write_index(index, "video_index.faiss") 
    
