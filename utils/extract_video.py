# 안쓰는 일회성 파일입니다. 주석 해제하지 마세요
# import os
# import json
# import yt_dlp
# import whisper
# from sentence_transformers import SentenceTransformer
# import asyncio
# import faiss

# # youtube_data.json 경로 설정
# YOUTUBE_DATA_PATH = os.path.join(os.path.dirname(__file__), "youtube_data.json")

# # 오디오 다운로드 경로 설정 (절대 경로 사용)
# output_dir = os.path.join(os.path.dirname(__file__), "downloads")
# os.makedirs(output_dir, exist_ok=True)

# # json 파일 로드
# try:
#     with open(YOUTUBE_DATA_PATH, "r") as f:
#         youtube_data = json.load(f)
# except FileNotFoundError:
#     raise FileNotFoundError(f"❌ ERROR: '{YOUTUBE_DATA_PATH}' 파일을 찾을 수 없습니다.")

# # whisper 모델 로드 (한 번만 로딩)
# model = whisper.load_model("small")

# # 비디오 오디오 추출 (비동기 처리)
# async def save_video_audio(url, video_id):
#     filename = os.path.join(output_dir, f"{video_id}.mp3")
    
#     ydl_opts = {
#         'format': 'bestaudio/best',
#         'outtmpl': filename[:-4],  # .mp3 확장자를 제외한 파일명 지정
#         'postprocessors': [{
#             'key': 'FFmpegExtractAudio',
#             'preferredcodec': 'mp3',
#             'preferredquality': '192',
#         }],
#         'postprocessor_args': ['-vn'],  # 비디오 비활성화 (오디오만)
#     }
    
#     with yt_dlp.YoutubeDL(ydl_opts) as ydl:
#         await asyncio.to_thread(ydl.download, [url])  # 비동기로 다운로드

#     # 다운로드된 파일 확장자 정리
#     if os.path.exists(f"{filename[:-4]}.mp3.mp3"):
#         os.rename(f"{filename[:-4]}.mp3.mp3", filename)
#     elif os.path.exists(f"{filename[:-4]}.mp3"):
#         os.rename(f"{filename[:-4]}.mp3", filename)

#     return filename if os.path.exists(filename) else None

# # 음성에서 텍스트 추출
# async def extract_video_text(audio_file):
#     if not os.path.exists(audio_file):
#         print(f"❌ 파일이 존재하지 않습니다: {audio_file}")
#         return None
    
#     result = await asyncio.to_thread(model.transcribe, audio_file)  # 비동기 텍스트 추출
#     print(f"🎙️ 변환된 텍스트: {result['text'][:100]}...")  # 긴 텍스트는 앞부분만 출력
#     return result["text"]

# async def process_videos():
#     for video in youtube_data:
#         print(f"🎬 다운로드 시작: {video['title']} ({video['video_id']})")

#         filename = await save_video_audio(video["url"], video["video_id"])
        
#         if filename:
#             print(f"✅ 저장된 파일 경로: {filename}")
#         else:
#             print(f"❌ {video['title']} 오디오 다운로드 실패")
#             continue

#         # 텍스트 변환
#         text = await extract_video_text(filename)
#         if text:
#             video["text"] = text  # 영상 내용 저장 -> 딕셔너리에 추가
#         else:
#             print(f"❌ {video['title']} 텍스트 변환 실패")

# # 비디오 텍스트 -> 벡터 DB
# async def vectorize_and_save():
#     print("🔍 FAISS 벡터화 시작...")
    
#     model = SentenceTransformer('all-MiniLM-L6-v2')
#     video_texts = [video["text"] for video in youtube_data if "text" in video]  # 변환된 텍스트 리스트
    
#     if not video_texts:
#         print("❌ 변환된 텍스트가 없습니다. 벡터화를 중단합니다.")
#         return

#     embeddings = model.encode(video_texts, convert_to_numpy=True)  # 벡터화

#     # FAISS 벡터 데이터베이스 생성 및 삽입
#     d = embeddings.shape[1]
#     index = faiss.IndexFlatL2(d)
#     index.add(embeddings)

#     # FAISS 인덱스를 파일로 저장
#     faiss_path = os.path.join(os.path.dirname(__file__), "youtube.faiss")
#     faiss.write_index(index, faiss_path)
#     print(f"✅ FAISS 인덱스 저장 완료: {faiss_path}")

# async def main():
#     print("🎬 YouTube 영상 처리 시작...")

#     # 1단계: 오디오 다운로드 및 텍스트 변환
#     await process_videos()

#     # 2단계: FAISS 인덱스 생성 및 저장
#     await vectorize_and_save()

#     print("🎉 모든 작업 완료!")

# # 실행
# asyncio.run(main())
