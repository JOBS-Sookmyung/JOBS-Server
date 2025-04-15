# 일회성 코드 -> 주석 해제하지 마세요.
'''
import os
import faiss
from sentence_transformers import SentenceTransformer
import pandas as pd
import numpy as np
import pickle
from tqdm import tqdm
import shutil
from datetime import datetime

def backup_existing_files():
    """기존 파일을 백업하는 함수"""
    base_path = ".."
    files_to_backup = ["faiss_index.jobkorea", "faiss_qa_mapping.pkl"]
    backup_dir = os.path.join(base_path, "backups")
    
    # 백업 디렉토리 생성
    if not os.path.exists(backup_dir):
        os.makedirs(backup_dir)
    
    # 현재 시간으로 백업 파일명 생성
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    for file in files_to_backup:
        source_path = os.path.join(base_path, file)
        if os.path.exists(source_path):
            backup_path = os.path.join(backup_dir, f"{file}.{timestamp}")
            shutil.copy2(source_path, backup_path)
            print(f"✅ {file} 백업 완료: {backup_path}")

# CSV 파일 불러오기
df = pd.read_csv('../data/jobkorea.csv')

# wide 형태를 tidy 형태로 변환하는 함수
def data_preprocess():
    qa_pairs = []
    for idx, row in df.iterrows():
        for i in range(1, 20):  # question1 ~ question19까지
            q_col = f'question{i}'
            a_col = f'answer{i}'
            if pd.notna(row.get(q_col)) and pd.notna(row.get(a_col)):
                qa_pairs.append({
                    'question': row[q_col],
                    'answer': row[a_col]
                })
    return pd.DataFrame(qa_pairs)

def process_batch(model, questions, batch_size=1000):
    """배치 처리를 위한 함수"""
    embeddings = []
    for i in tqdm(range(0, len(questions), batch_size), desc="Processing batches"):
        batch = questions[i:i+batch_size]
        batch_embeddings = model.encode(batch, show_progress_bar=False)
        embeddings.append(batch_embeddings)
    return np.vstack(embeddings)

def main():
    # 0. 기존 파일 백업
    print("기존 파일 백업 중...")
    backup_existing_files()
    
    # 1. 데이터 전처리
    print("데이터 전처리 시작...")
    qa_df = data_preprocess()
    print(f"전처리 완료. 총 {len(qa_df)}개의 QA 쌍 생성")

    # 2. 임베딩 모델 로드
    print("임베딩 모델 로딩 중...")
    model = SentenceTransformer('sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2')

    # 3. 질문 임베딩 (배치 처리)
    print("질문 임베딩 생성 중...")
    questions = qa_df['question'].tolist()
    question_embeddings = process_batch(model, questions)
    print(f"임베딩 생성 완료. 차원: {question_embeddings.shape}")

    # 4. FAISS 인덱스 생성 (cosine similarity를 위한 L2 normalize)
    print("FAISS 인덱스 생성 중...")
    dimension = question_embeddings.shape[1]
    index = faiss.IndexIVFFlat(faiss.IndexFlatL2(dimension), dimension, 100)
    index.train(question_embeddings)
    print("인덱스 생성 완료")

    # 5. 인덱스와 매핑 정보를 저장
    print("결과 저장 중...")
    faiss.write_index(index, "./faiss_index.jobkorea")  # 벡터 인덱스 -> 인덱스로 아래 질문/답변이랑 연결지어야함
    with open("./faiss_qa_mapping.pkl", "wb") as f:  # 질문/답변 매핑 정보
        pickle.dump(qa_df.to_dict(orient='records'), f)
    print("저장 완료")

    print("✅ 임베딩 및 FAISS 인덱싱 완료!")

# 🔥 실행 트리거
if __name__ == "__main__":
    main()
'''