# PDF 파일 저장소
pdf_files = {}  # 전역 변수로 PDF 파일 정보 저장

def add_pdf(token: str, data: dict):
    """PDF 파일 정보를 저장소에 추가"""
    pdf_files[token] = data
    print(f"✅ PDF 정보 저장 완료 - 토큰: {token}")
    print(f"📝 현재 저장된 토큰들: {list(pdf_files.keys())}")

def get_pdf(token: str) -> dict:
    """토큰으로 PDF 파일 정보 조회"""
    return pdf_files.get(token, {})

def remove_pdf(token: str):
    """PDF 파일 정보 삭제"""
    if token in pdf_files:
        del pdf_files[token]
        print(f"✅ PDF 정보 삭제 완료 - 토큰: {token}")

# 디버깅용 함수 추가
def print_pdf_files():
    print("현재 저장된 PDF 파일들:", pdf_files)

