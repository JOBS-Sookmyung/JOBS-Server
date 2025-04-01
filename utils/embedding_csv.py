# 일회성 코드 -> 주석 해제하지 마세요.
'''
# 일회성 코드 -> 주석 해제하지 마세요.
import os
import faiss
from sentence_transformers import SentenceTransformer
import pandas as pd
import numpy as np
import pickle

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

def main():
    # 1. 데이터 전처리
    qa_df = data_preprocess()

    # 2. 임베딩 모델 로드
    model = SentenceTransformer('sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2')

    # 3. 질문 임베딩
    questions = qa_df['question'].tolist()
    question_embeddings = model.encode(questions, show_progress_bar=True)

    # 4. FAISS 인덱스 생성 (cosine similarity를 위한 L2 normalize)
    dimension = question_embeddings.shape[1]
    index = faiss.IndexFlatL2(dimension)  # cosine similarity = L2 on normalized vectors
    faiss.normalize_L2(question_embeddings)
    index.add(np.array(question_embeddings))

    # 5. 인덱스와 매핑 정보를 저장
    faiss.write_index(index, "../faiss_index.jobkorea")  # 벡터 인덱스 -> 인덱스로 아래 질문/답변이랑 연결지어야함
    with open("../faiss_qa_mapping.pkl", "wb") as f:  # 질문/답변 매핑 정보
        pickle.dump(qa_df.to_dict(orient='records'), f)

    print("✅ 임베딩 및 FAISS 인덱싱 완료!")

# 🔥 실행 트리거
if __name__ == "__main__":
    main()
'''