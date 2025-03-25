# PDF 파일 저장소
import logging

logger = logging.getLogger(__name__)

class PDFStorage:
    def __init__(self):
        self._pdf_files = {}

    def add_pdf(self, token: str, data: dict):
        """PDF 파일 정보를 저장소에 추가"""
        self._pdf_files[token] = data
        logger.info(f"PDF 저장소에 추가됨 - 토큰: {token}")
        logger.info(f"현재 저장된 토큰들: {list(self._pdf_files.keys())}")

    def get_pdf(self, token: str) -> dict:
        """토큰으로 PDF 파일 정보 조회"""
        pdf_data = self._pdf_files.get(token)
        if pdf_data is None:
            logger.error(f"토큰에 해당하는 PDF 데이터가 없음: {token}")
            return None
        logger.info(f"PDF 데이터 조회 성공 - 토큰: {token}")
        return pdf_data

    def print_pdf_files(self):
        """디버깅용 함수"""
        logger.info(f"현재 저장된 PDF 파일들: {list(self._pdf_files.keys())}")

# 전역 인스턴스 생성
pdf_storage = PDFStorage()

