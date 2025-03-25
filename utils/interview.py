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
        self.token = token
        self.llm = OpenAI(api_key=API_KEY, temperature=0.7)
        
        # PDF 데이터 로드
        pdf_data = pdf_storage.get_pdf(token)
        if not pdf_data:
            raise ValueError(f"토큰 {token}에 해당하는 PDF 데이터가 없습니다.")
        
        self.resume = pdf_data.get("resume_text", "")
        self.recruit_url = pdf_data.get("recruitUrl", "")
        
        if not self.resume or not self.recruit_url:
            raise ValueError("이력서 또는 채용공고 URL이 없습니다.")
        
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
        
        self.mock_data_path = mock_data_path
        self.example_questions = self._load_mock_interview_data(mock_data_path)

    def _load_mock_interview_data(self, mock_data_path=None):
        if not mock_data_path:
            mock_data_path = os.path.join(FILE_DIR, "mock_interview_data.json")
        
        try:
            if os.path.exists(mock_data_path):
                df = pd.read_json(mock_data_path)
                return "\n".join(df['question'].tolist()[:5])
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
            # 이미 생성된 질문이 있는 경우 반환
            if self.main_questions:
                logger.info("이미 생성된 질문이 있습니다.")
                return self.main_questions

            logger.info("새로운 대표질문 생성 시작")
            
            # 프롬프트 준비
            prompt = PromptTemplate(
                template=self._get_question_template(),
                input_variables=['resume', 'recruit_url', 'example_questions']
            )
            
            # LLMChain 생성 및 실행
            chain = LLMChain(prompt=prompt, llm=self.llm)
            
            try:
                response = await chain.ainvoke({
                    'resume': self.resume[:1000],  # 이력서 텍스트 길이 제한
                    'recruit_url': self.recruit_url,
                    'example_questions': self.example_questions
                })
                
                if not response or not isinstance(response, dict):
                    logger.error(f"잘못된 응답 형식: {response}")
                    raise ValueError("질문 생성 실패")
                
                # 응답에서 질문 추출 및 정제
                questions_text = response.get('text', '').strip()
                if not questions_text:
                    logger.error("응답에서 텍스트를 찾을 수 없습니다.")
                    raise ValueError("질문 생성 실패")
                
                # 질문 분리 및 저장
                questions = [q.strip() for q in questions_text.split('\n') if q.strip()]
                if not questions:
                    logger.error("질문을 추출할 수 없습니다.")
                    raise ValueError("질문 생성 실패")
                
                # 최대 5개 질문만 저장
                self.main_questions = questions[:5]
                logger.info(f"대표질문 {len(self.main_questions)}개 생성 완료")
                
                return self.main_questions
                    
            except Exception as e:
                logger.error(f"LLM 체인 실행 중 오류: {str(e)}")
                raise
            
        except Exception as e:
            logger.error(f"대표질문 생성 중 오류 발생: {str(e)}")
            raise ValueError("대표질문을 생성할 수 없습니다.")

    async def check_session_completion(self):
        """세션이 완료되었는지 확인하고 상태를 업데이트하는 메서드"""
        try:
            # 모든 대표질문에 대해 충분한 답변이 있는지 확인
            if self.current_main >= len(self.main_questions):
                # DB에서 세션 상태 업데이트
                db = SessionLocal()
                try:
                    session = db.query(InterviewSessionDB).filter_by(session_token=self.token).first()
                    if session:
                        session.status = "completed"
                        db.commit()
                        logger.info(f"세션 {self.token} 완료 처리됨")
                except Exception as e:
                    logger.error(f"세션 상태 업데이트 중 오류: {str(e)}")
                    db.rollback()
                finally:
                    db.close()
                return True
            return False
        except Exception as e:
            logger.error(f"세션 완료 확인 중 오류: {str(e)}")
            return False

    async def generate_main_question(self):
        """저장된 대표 질문을 하나씩 반환하는 메서드"""
        try:
            # 질문이 없으면 생성
            if not self.main_questions:
                logger.info("대표질문 새로 생성")
                self.main_questions = await self.generate_main_questions()
                if not self.main_questions:
                    logger.error("대표질문 생성 실패")
                    return None
            
            # 현재 대표질문 인덱스 확인
            if self.current_main >= len(self.main_questions):
                logger.info("모든 대표질문이 반환되었습니다.")
                # 세션 완료 여부 확인
                await self.check_session_completion()
                return None

            # 현재 질문 반환
            question = self.main_questions[self.current_main]
            logger.info(f"대표질문 {self.current_main + 1} 반환: {question}")
            
            return question
            
        except Exception as e:
            logger.error(f"질문 반환 중 오류: {str(e)}")
            raise ValueError("대표질문을 생성할 수 없습니다.")

    # 꼬리질문 생성
    async def generate_follow_up(self, last_answer: str):
        """사용자 답변을 바탕으로 꼬리질문을 생성하는 메서드"""
        try:
            # 현재 대표질문에 대한 꼬리질문 개수 확인
            if len(self.follow_up_questions[self.current_main]) >= self.answer_per_question - 1:
                logger.warning(f"더 이상의 꼬리질문이 없습니다. (대표질문 {self.current_main + 1})")
                return "더 이상의 꼬리질문이 없습니다."
            
            # 현재 대표질문 가져오기
            current_main_question = self.main_questions[self.current_main] if self.main_questions else ""
            
            # 프롬프트 준비
            prompt = PromptTemplate(
                template=self._get_follow_up_template(),
                input_variables=['main_question', 'answer', 'previous_follow_ups']
            )
            
            # 이전 꼬리질문들 컨텍스트 구성
            previous_follow_ups = "\n".join(self.follow_up_questions[self.current_main])
            
            # LLMChain 생성 및 실행
            chain = LLMChain(prompt=prompt, llm=self.llm)
            response = await chain.ainvoke({
                'main_question': current_main_question,
                'answer': last_answer,
                'previous_follow_ups': previous_follow_ups
            })
            
            if not response or not isinstance(response, dict):
                logger.error(f"잘못된 응답 형식: {response}")
                return "꼬리질문을 생성할 수 없습니다."
            
            # 응답에서 텍스트 추출 및 정제
            question = response.get('text', '').strip()
            if not question:
                logger.error("응답에서 텍스트를 찾을 수 없습니다.")
                return "꼬리질문을 생성할 수 없습니다."

            # DB에 저장
            db = SessionLocal()
            try:
                session = db.query(InterviewSessionDB).filter_by(session_token=self.token).first()
                if not session:
                    logger.error(f"세션을 찾을 수 없음: {self.token}")
                    return "꼬리질문을 생성할 수 없습니다."

                new_follow_up = ChatMessageDB(
                    session_id=session.id,
                    message_type="follow_up",
                    content=question
                )
                db.add(new_follow_up)
                db.commit()
                db.refresh(new_follow_up)
                
                # 꼬리질문 저장
                self.follow_up_questions[self.current_main].append(question)
                logger.info(f"꼬리질문 생성 성공 (대표질문 {self.current_main + 1}): {question}")
                return question
                
            except Exception as e:
                logger.error(f"DB 저장 중 오류: {str(e)}")
                db.rollback()
                return "꼬리질문을 생성할 수 없습니다."
            finally:
                db.close()

        except Exception as e:
            logger.error(f"꼬리질문 생성 중 오류: {str(e)}")
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
        """사용자 답변에 대한 피드백을 생성하는 메서드"""
        try:
            # 현재 대표질문 가져오기
            current_main_question = self.main_questions[self.current_main] if self.main_questions else ""
            
            # 이전 피드백들 컨텍스트 구성
            previous_feedbacks = "\n".join(self.feedbacks[self.current_main])
            
            # 프롬프트 준비
            prompt = PromptTemplate(
                template=self._get_feedback_template(),
                input_variables=['main_question', 'answer', 'previous_feedbacks']
            )
            
            # LLMChain 생성 및 실행
            chain = LLMChain(prompt=prompt, llm=self.llm)
            response = await chain.ainvoke({
                'main_question': current_main_question,
                'answer': last_answer,
                'previous_feedbacks': previous_feedbacks
            })
            
            if not response or not isinstance(response, dict):
                logger.error(f"잘못된 응답 형식: {response}")
                return "피드백을 생성할 수 없습니다."
            
            # 응답에서 텍스트 추출 및 정제
            feedback = response.get('text', '').strip()
            if not feedback:
                logger.error("응답에서 텍스트를 찾을 수 없습니다.")
                return "피드백을 생성할 수 없습니다."

            # DB에 저장
            db = SessionLocal()
            try:
                session = db.query(InterviewSessionDB).filter_by(session_token=self.token).first()
                if not session:
                    logger.error(f"세션을 찾을 수 없음: {self.token}")
                    return "피드백을 생성할 수 없습니다."

                new_feedback = ChatMessageDB(
                    session_id=session.id,
                    message_type="feedback",
                    content=feedback
                )
                db.add(new_feedback)
                db.commit()
                db.refresh(new_feedback)
                    
                # 피드백 저장
                self.feedbacks[self.current_main].append(feedback)
                logger.info(f"피드백 생성 성공 (대표질문 {self.current_main + 1}): {feedback}")
                return feedback
                
            except Exception as e:
                logger.error(f"DB 저장 중 오류: {str(e)}")
                db.rollback()
                return "피드백을 생성할 수 없습니다."
            finally:
                db.close()

        except Exception as e:
            logger.error(f"피드백 생성 중 오류: {str(e)}")
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
        5. Do not add numbering or indexing to the questions (like "1. ", "2. ", etc.).
        '''

    def _get_follow_up_template(self):
        return '''
        You are an expert AI job interviewer.

        [Current Main Question]
        {main_question}

        [Candidate's Answer]
        {answer}

        [Previous Follow-up Questions]
        {previous_follow_ups}
        
        Create a follow-up question that:
        1. Be in Korean.
        2. Must be different from the previous follow-up questions.
        3. Must be specifically related to the candidate's answer and the main question.
        4. Focus on:
           - Specific examples or situations mentioned
           - Technical details or methodologies used
           - Challenges faced and solutions implemented
           - Results and impacts achieved
        5. Be concise and direct.
        6. Only provide the follow-up question, without any additional explanations or comments.
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

    def _get_feedback_template(self):
        return '''
        You are an expert Korean career coach.  
        Based on the provided question and answer, write professional and helpful interview feedback in Korean.

        [질문]
        {main_question}

        [답변]
        {answer}

        [작성 지침]
        - 반드시 세 문장 이내로 작성합니다.
        - 첫 번째 문장: 답변의 강점을 2~3가지 구체적으로 칭찬합니다. (구조, 논리, 표현, 직무 연관성 등)
        - 두 번째 문장: 개선할 점 1~2가지를 구체적이고 친절하게 제시합니다. (예: 더 구체적이어야 한다, 논리 흐름이 약하다 등)
        '''

     