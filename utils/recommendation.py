import os
import pandas as pd
import whisper # install 할 때, openai-whisper로 설치해야함

model = whisper.load_model("base")  # 모델 불러오기
result = model.transcribe("video.mp4")  # 영상 음성 → 텍스트 변환

print(result["text"])  # 추출된 텍스트 출력