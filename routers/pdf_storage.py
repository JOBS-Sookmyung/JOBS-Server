# PDF 파일 저장소
class PDFStorage:
    def __init__(self):
        self._pdf_files = {}

    def add_pdf(self, token: str, data: dict):
        """PDF 파일 정보를 저장소에 추가"""
        self._pdf_files[token] = data
        print(f"📝 PDF 저장소에 추가됨 - 토큰: {token}")
        print(f"📝 현재 저장된 토큰들: {list(self._pdf_files.keys())}")

    def get_pdf(self, token: str) -> dict:
        """토큰으로 PDF 파일 정보 조회"""
        return self._pdf_files.get(token, {})

    def print_pdf_files(self):
        """디버깅용 함수"""
        print("현재 저장된 PDF 파일들:", self._pdf_files)

# 전역 인스턴스 생성
pdf_storage = PDFStorage()

