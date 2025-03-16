# faiss 확인용 코드 -> 추후 삭제할 것!
import faiss
import numpy as np

# FAISS 인덱스 로드
faiss_path = "/Users/jeongsu-in/JOBS-Server-2/utils/youtube.faiss"  # 저장된 FAISS 파일 경로
index = faiss.read_index(faiss_path)

# 첫 번째 벡터 가져오기
vec = np.zeros((1, index.d), dtype=np.float32)  # 빈 벡터 생성
index.reconstruct(0, vec[0])  # 첫 번째 벡터 복원

print(f"🧬 첫 번째 벡터 샘플 (일부 출력): {vec[0][:10]}...")  # 앞 10개 요소만 출력

