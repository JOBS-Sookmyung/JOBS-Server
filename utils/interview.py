import os
import pandas as pd
from PyPDF2 import PdfReader
import openai
from langchain.prompts import PromptTemplate
from langchain.chains import LLMChain
from langchain_openai import OpenAI
from routers.pdf_storage import pdf_storage
from config import FILE_DIR, API_KEY
from db import SessionLocal, InterviewSessionDB, ChatMessageDB
from typing import Optional, Dict, Any
import logging

logger = logging.getLogger(__name__)

class InterviewSession:
    def __init__(self, token: str, question_num=5, answer_per_question=5, mock_data_path=None):
        self.token = token  # PDF 업로드 시 생성된 토큰 사용
        self.llm = OpenAI(api_key=API_KEY)
        
        # PDF 데이터 로드
        pdf_data = pdf_storage.get_pdf(token)
        if not pdf_data:
            raise ValueError(f"토큰 {token}에 해당하는 PDF 데이터가 없습니다.")
        
        self.resume = pdf_data.get("resume_text")
        self.recruit_url = pdf_data.get("recruitUrl")
        
        # 세션 상태 초기화
        self.current_main = 0
        self.current_follow_up = 0
        self.current_answer = 0
        self.question_num = question_num
        self.answer_per_question = answer_per_question
        self.main_questions = []
        self.follow_up_questions = [[] for _ in range(question_num)]
        self.answers = [[] for _ in range(question_num)]
        self.hints = [[] for _ in range(question_num)]
        self.feedbacks = [[] for _ in range(question_num)]
        
        # DB 세션 확인 및 초기화는 외부에서 처리하도록 변경
        self.mock_data_path = mock_data_path
        self.example_questions = self._load_mock_interview_data(mock_data_path)

    def _load_mock_interview_data(self, mock_data_path=None):
        """모의 면접 데이터를 로드하는 메서드"""
        if not mock_data_path:
            mock_data_path = os.path.join(FILE_DIR, "mock_interview_data.json")
        
        try:
            # 🔥 수정됨: JSON 파일이 없을 경우 기본 질문 리스트 제공
            if os.path.exists(mock_data_path):
                df = pd.read_json(mock_data_path)
                return "\n".join(df['question'].tolist()[:5])  # 상위 5개 질문만 사용
            else:
                return """
                프로젝트에서 가장 큰 도전 과제는 무엇이었나요?
                팀 프로젝트에서 갈등이 발생했을 때 어떻게 해결하셨나요?
                기술 스택을 선택한 이유는 무엇인가요?
                프로젝트에서 본인의 역할은 무엇이었나요?
                가장 성공적으로 완료한 프로젝트는 무엇인가요?
                """
        except Exception as e:
            print(f"모의 면접 데이터 로딩 실패: {str(e)}")
            return ""

    async def generate_main_questions(self, num_questions: int = 5):
        """대표 질문을 생성하는 메서드"""
        try:
            # 이미 생성된 질문이 있는 경우, 현재 인덱스의 질문 반환
            if self.main_questions:
                if self.current_main < len(self.main_questions):
                    current_question = self.main_questions[self.current_main]
                    return current_question
                return "더 이상의 대표질문이 없습니다."
            
            # 처음 호출 시 5개의 질문을 모두 생성하여 저장
            for _ in range(num_questions):
                question = await self.generate_main_question()
                if question:
                    self.main_questions.append(question)
            
            # 첫 번째 질문 반환
            if self.main_questions:
                return self.main_questions[0]
            
            return "대표질문을 생성할 수 없습니다."
            
        except Exception as e:
            print(f"Error: {str(e)}")
            return "대표질문을 생성할 수 없습니다."

    async def generate_main_question(self):
        try:
            if len(self.main_questions) >= self.question_num:
                return None
            
            prompt = PromptTemplate(
                template=self._get_question_template(),
                input_variables=['resume', 'job_url']
            )
            chain = LLMChain(prompt=prompt, llm=self.llm)

            response = chain.run({
                'resume': self.resume,
                'job_url': self.recruit_url
            }).strip()
            
            # 응답에서 개별 질문 추출
            questions = []
            for line in response.split('\n'):
                line = line.strip()
                if line and any(f"{i}." in line for i in range(1, 10)):
                    # 숫자와 점 이후의 텍스트만 추출
                    question = line.split(".", 1)[1].strip()
                    questions.append(question)
            
            # 현재 필요한 질문만 선택
            if questions:
                question = questions[len(self.main_questions)]  # 현재 인덱스에 해당하는 질문 선택
            else:
                return "질문을 생성할 수 없습니다."
            
            # DB에 저장
            db = SessionLocal()
            try:
                session = db.query(InterviewSessionDB).filter_by(session_token=self.token).first()
                if not session:
                    return None
                
                new_question = ChatMessageDB(
                    session_id=session.id,
                    message_type="main_question",
                    content=question
                )
                db.add(new_question)
                db.commit()
                db.refresh(new_question)
                
                self.main_questions.append(question)
                return question
                    
            except Exception as e:
                db.rollback()
                return None
            finally:
                db.close()
            
        except Exception as e:
            print(f"Error: {str(e)}")
            return None

    # 꼬리질문 생성
    async def generate_follow_up(self, last_answer: str):
        try:
            if len(self.follow_up_questions[self.current_main]) >= self.answer_per_question - 1:
                return "더 이상의 꼬리질문이 없습니다."
            
            prompt = PromptTemplate(template=self._get_follow_up_template(), input_variables=['answer'])
            chain = LLMChain(prompt=prompt, llm=self.llm)
            question = chain.run({'answer': last_answer})
            question = question.strip() if question else "꼬리질문을 생성할 수 없습니다."

            # DB에 저장
            db = SessionLocal()
            try:
                session = db.query(InterviewSessionDB).filter_by(session_token=self.token).first()
                if not session:
                    return question

                new_follow_up = ChatMessageDB(
                    session_id=session.id,
                    message_type="follow_up",
                    content=question
                )
                db.add(new_follow_up)
                db.commit()
                db.refresh(new_follow_up)
                
                self.follow_up_questions[self.current_main].append(question)
                return question
            finally:
                db.close()

        except Exception as e:
            print(f"Error: {str(e)}")
            return "꼬리질문을 생성할 수 없습니다."

    def store_user_answer(self, session_id: int, answer: str):
        """사용자의 답변을 저장합니다."""
        try:
            # 현재 질문 인덱스에 답변 저장
            if 0 <= self.current_main < len(self.answers):
                self.answers[self.current_main].append(answer)
                print(f"✅ 답변 저장 완료 - 질문 {self.current_main + 1}")
            else:
                print(f"⚠️ 답변 저장 실패 - 유효하지 않은 질문 인덱스: {self.current_main}")
        except Exception as e:
            print(f"❌ 답변 저장 중 오류 발생: {str(e)}")
            raise

    async def generate_hint(self, question, question_index):
        try:
            print(f"힌트 생성 시작 - 질문 인덱스: {question_index}, 질문: {question}")
            
            # 이력서 텍스트 길이 제한
            resume_text = self.resume[:1000] if len(self.resume) > 1000 else self.resume
            
            prompt = PromptTemplate(
                template=self._get_hint_template(),
                input_variables=['resume', 'question', 'question_index']
            )
            chain = LLMChain(prompt=prompt, llm=self.llm)
            
            hint = chain.run({
                'resume': resume_text,
                'question': question,
                'question_index': question_index
            })
            
            if not hint:
                raise ValueError(f"질문 {question_index}에 대한 힌트가 생성되지 않았습니다.")
            
            hint = hint.strip()
            print(f"생성된 힌트 (질문 {question_index}): {hint}")
            
            # 힌트를 세션의 힌트 리스트에 저장
            if 0 <= question_index < len(self.hints):
                self.hints[question_index].append(hint)
            
            return hint
            
        except Exception as e:
            print(f"힌트 생성 중 오류 발생 (질문 {question_index}): {str(e)}")
            return f"질문 {question_index}에 대한 힌트를 생성할 수 없습니다."

    async def generate_feedback(self, last_answer: str):
        try:
            prompt = PromptTemplate(template=self._get_feedback_template(), input_variables=['answer'])
            chain = LLMChain(prompt=prompt, llm=self.llm)
            feedback = chain.run({'answer': last_answer})
            feedback = feedback.strip() if feedback else "피드백을 생성할 수 없습니다."

            # DB에 저장
            db = SessionLocal()
            try:
                session = db.query(InterviewSessionDB).filter_by(session_token=self.token).first()
                if session:
                    new_feedback = ChatMessageDB(
                        session_id=session.id,
                        message_type="feedback",
                        content=feedback
                    )
                    db.add(new_feedback)
                    db.commit()
                    
                    self.feedbacks[self.current_main].append(feedback)
                return feedback
            finally:
                db.close()

        except Exception as e:
            print(f"Error: {str(e)}")
            return "피드백을 생성할 수 없습니다."

    def _get_question_template(self):
        return f'''
        다음 이력서와 채용 공고를 바탕으로 면접 질문을 생성해주세요.

        [이력서]
        {self.resume[:1000]}  # 이력서 텍스트를 1000자로 제한

        [채용 공고]
        {self.recruit_url[:500]}  # 채용 공고 URL을 500자로 제한

        [예시 질문]
        {self.example_questions}

        요구사항:
        1. Be in Korean.
        2. Be specific and tailored to the resume.
        3. Be similar to the example questions.
        4. Write only the question, without additional explanations or comments.
        '''

    def _get_follow_up_template(self):
        return f'''
        You are an expert AI job interviewer.
        Use the following answer from a candidate to create a follow-up question in Korean:
        {{answer}}

        The follow-up question must:
        1. Be in Korean.
        2. You must avoid repetition of previously generated questions.
        3. Be specific and you must focus on details mentioned in the answer.
        4. Explore the reasoning, challenges, results, or methodology in the answer.
        5. Be realistic and appropriate for a job interview setting.
        6. Only provide one follow-up question at a time.
        7. Provide only the follow-up question, without any additional explanations or comments.
        '''

    def _get_hint_template(self):       # 힌트 생성 프롬프트 템플릿
        return f'''
        [Resume Context]
        {self.resume}

        [Current Question]
        {{question}}

        [Guidelines]
        1. Extract three key technical keywords to emphasize in the response.  
        2. Suggest applying the STAR (Situation-Task-Action-Result) method.  
        3. Recommend using specific numbers/data.  
        4. Provide advice summarized in no more than two sentences.
        5. Be in Korean.
        6. Be specific and tailored to the resume.
        7. Only one question at a time.
        '''

    def _get_feedback_template(self):   # 피드백 생성 프롬프트 템플릿
        return f'''
        The feedback must:
        1. Compliment specific strengths in the answer.
        2. Identify areas where the answer could be more specific or detailed.
        3. Provide concrete examples or suggestions for improvement directly related to the details mentioned in the answer.
        4. Be realistic and appropriate for a professional job interview setting.
        5. Be written in Korean, formatted with clear and professional language.
        6. Always include encouraging comments and actionable advice with a kind and supportive tone.
        7. A complete response within the 1,750-token limit of GPT-4 Turbo.
        
        Example Feedback:
        "우선, 팀원들의 장점과 관심사를 파악하기 위해 본인이 한 노력의 단계와 과정을 구체적으로 설명하신 부분은 훌륭합니다! 다만 구체적인 경험, 예를 들어 '애니를 좋아하는 친구와의 라포를 형성하기 위해 요즘 유행하는 넷플릭스 애니메이션 이름을 언급하며 가까워질 수 있었습니다'와 같은 구체적인 예시가 부족해 보입니다. 다음에는 이런 부분을 언급하면서 답변하면 더욱더 신뢰감을 줄 수 있어 좋을 것으로 보입니다! 👏"
        
        When giving examples or suggestions, tailor them to the candidate's answer to make them relevant and specific. Avoid reusing generic or unrelated examples.
        Provide the feedback only, without additional explanations or comments in Korean.
        '''

     