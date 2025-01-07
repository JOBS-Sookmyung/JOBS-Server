import os
# OpenAI API 키 설정
# os.environ ... => Dotenv로 대체 필요함

# !pip install -q langchain openai transformers torch langchain.community fitz frontend pymupdf
from langchain.prompts import PromptTemplate
from langchain.chains import LLMChain
from langchain.llms import OpenAI
from routers import pdf_files
from config import FILE_DIR
from utils import load_pdf_to_text, summarize_text

# 질문 및 답변 관리 클래스
class InterviewSession:
    def __init__(self, token: str, question_num=5):
        self.token = token
        self.question_num = question_num

        self.question_index = 0
        self.questions = []
        self.answers = []

        # 이력서 텍스트 로드
        self.resume = self._load_pdf_to_resume()

        # 예시 질문 템플릿
        self.example_questions = '''
        질문 1: 객체지향 프로그래밍(OOP)의 4대 원칙은 무엇이며, 각각을 설명해주세요.
        질문 2: RESTful API란 무엇이며, 설계 원칙을 설명해주세요.
        질문 3: 데이터베이스 인덱스(Index)란 무엇이며, 어떤 상황에서 사용해야 하나요?
        질문 4: 자바(Java)에서 메모리 관리 방식에 대해 설명해주세요.
        질문 5: Git에서 브랜치(branch)를 사용할 때의 이점은 무엇인가요?
        '''

        # 프롬프트 템플릿 설정
        self.template = f'''
        You are an expert AI interviewer.
        Use the following resume to make a question in Korean:
        {self.resume}

        Here are example questions from a mock interview dataset:
        {self.example_questions}

        The question must:
        1. Be in Korean.
        2. Be specific and tailored to the details of the resume.
        3. Focus on the skills, experiences, or projects mentioned.
        4. Avoid repetition of previously generated questions.
        5. Be similar in style and detail to the examples provided.

        Provide only the question, without any additional explanations or comments.
        '''
        self.prompt = PromptTemplate(template=self.template, input_variables=['resume'])
        self.llm = OpenAI()
        self.llm_chain = LLMChain(prompt=self.prompt, llm=self.llm)

    def _load_pdf_to_resume(self):
        if self.token not in pdf_files:
            raise ValueError("해당 토큰에 대한 PDF 파일이 존재하지 않습니다.")

        pdf_path = os.path.join(FILE_DIR, f"{self.token}.pdf")
        if not os.path.exists(pdf_path):
            raise FileNotFoundError("PDF 파일이 존재하지 않습니다.")

        # PDF 텍스트 읽기 및 요약
        pdf_text = load_pdf_to_text(pdf_path)
        summarized_text = summarize_text(pdf_text, max_length=1500)
        return summarized_text

    async def generate_next_question(self):
        if self.question_index >= self.question_num:
            return None  # 최대 {question_num} 단계 질문

        question = await self._generate_question()
        self.questions.append(question)
        self.question_index += 1
        return {"index": self.question_index, "question": question}

    async def add_answer(self, answer):
        self.answers.append(answer)
        self.resume += f"\n질문 {self.question_index}: {self.questions[-1]}\n답변 {self.question_index}: {answer}"

    async def _generate_question(self):
        return await self.llm_chain.arun(resume=self.resume)
