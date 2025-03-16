from sqlalchemy.orm import Session
from PyPDF2 import PdfReader
import openai
import requests
from db import InterviewSessionDB, MainQuestionDB, FollowUpDB
from langchain.prompts import PromptTemplate
from langchain.chains import LLMChain
from langchain.llms import OpenAI
from config import API_KEY, FILE_DIR
import os

class InterviewSession:
    def __init__(self, token: str, pdf_path: str = None, url: str = None, db: Session = None):
        """인터뷰 세션을 초기화하고, PDF 또는 URL을 분석하여 요약."""
        self.token = token
        self.db = db
        self.pdf_path = pdf_path
        self.url = url
        self.llm = OpenAI(api_key=API_KEY)
        self.resume_summary = self._process_input()

    def _process_input(self):
        """PDF 또는 URL을 처리하여 요약된 텍스트를 반환."""
        if self.pdf_path:
            return self._summarize_text(self._load_pdf_to_text(self.pdf_path))
        elif self.url:
            return self._summarize_text(self._fetch_url_content(self.url))
        return ""
    
    def _load_pdf_to_text(self, pdf_path):
        """PDF에서 텍스트를 추출."""
        text = ""
        reader = PdfReader(pdf_path)
        for page in reader.pages:
            text += page.extract_text() + "\n"
        return text.strip()
    
    def _fetch_url_content(self, url):
        """주어진 URL에서 텍스트 데이터를 가져옴."""
        response = requests.get(url)
        return response.text if response.status_code == 200 else ""
    
    def _summarize_text(self, text, max_length=1500):
        """텍스트를 요약하여 반환."""
        client = openai.OpenAI(api_key=API_KEY)
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are an intelligent summarization assistant."},
                {"role": "user", "content": f"Summarize this text: {text}"}
            ],
            max_tokens=max_length
        )
        return response.choices[0].message.content.strip()
    
    async def generate_main_question(self):
        """요약된 내용을 기반으로 대표 질문을 생성."""
        prompt = PromptTemplate(template=self._get_question_template(), input_variables=['resume'])
        chain = LLMChain(prompt=prompt, llm=self.llm)
        question = await chain.arun({'resume': self.resume_summary})
        return question.strip()
    
    async def generate_follow_up(self, last_answer: str):
        """사용자의 답변을 기반으로 꼬리질문을 생성."""
        prompt = PromptTemplate(template=self._get_follow_up_template(), input_variables=['answer'])
        chain = LLMChain(prompt=prompt, llm=self.llm)
        question = await chain.arun({'answer': last_answer})
        return question.strip()
    
    async def generate_hint(self, question: str):
        """질문에 대한 힌트를 생성."""
        prompt = PromptTemplate(template=self._get_hint_template(), input_variables=['question'])
        chain = LLMChain(prompt=prompt, llm=self.llm)
        hint = await chain.arun({'question': question})
        return hint.strip()
    
    async def generate_feedback(self, answer: str):
        """사용자의 답변을 평가하고, 피드백과 점수를 생성."""
        prompt = PromptTemplate(template=self._get_feedback_template(), input_variables=['answer'])
        chain = LLMChain(prompt=prompt, llm=self.llm)
        feedback = await chain.arun({'answer': answer})
        
        # 피드백에서 점수를 추출하는 로직 (예제 방식)
        clarity_score = 4  # 명확성 점수 (예제 값)
        relevance_score = 5  # 관련성 점수 (예제 값)
        return feedback.strip(), clarity_score, relevance_score
    
    def _get_question_template(self):
        """대표 질문을 생성하기 위한 프롬프트 템플릿."""
        return """
        You are an expert AI interviewer.
        Use the following resume summary to create a main interview question in Korean:
        {resume}
        """
    
    def _get_follow_up_template(self):
        """꼬리 질문을 생성하기 위한 프롬프트 템플릿."""
        return """
        Given the following answer, generate a follow-up question in Korean.
        Answer: {answer}
        """
    
    def _get_hint_template(self):
        """질문에 대한 힌트를 생성하기 위한 프롬프트 템플릿."""
        return """
        Given the following question, generate a helpful hint in Korean.
        Question: {question}
        """
    
    def _get_feedback_template(self):
        """사용자의 답변을 평가하고 점수를 부여하는 프롬프트 템플릿."""
        return """
        Analyze the following answer and provide a structured feedback with clarity and relevance scores (1-5).
        Answer: {answer}
        """
