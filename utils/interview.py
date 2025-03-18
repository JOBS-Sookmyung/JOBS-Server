import os
import pandas as pd
from PyPDF2 import PdfReader
import openai
from langchain.prompts import PromptTemplate
from langchain.chains import LLMChain
from langchain_community.llms import OpenAI
from routers.pdf_storage import pdf_storage
from config import FILE_DIR, API_KEY
from db import SessionLocal, MainQuestionDB, FollowUpDB, InterviewSessionDB
from typing import Optional, Dict, Any

class InterviewSession:
    def __init__(self, token: str, question_num=5, answer_per_question=5, mock_data_path=None):
        self.token = token
        
        # PDF 데이터 로드
        pdf_data = pdf_storage.get_pdf(token)
        if not pdf_data:
            print(f"⚠️ PDF 데이터를 찾을 수 없음: {token}")
            # 기본값으로 초기화
            self.resume = "이력서 데이터가 없습니다."
            self.recruit_url = "채용 공고 URL이 없습니다."
        else:
            self.resume = pdf_data.get("resume_text", "이력서 텍스트를 가져올 수 없습니다.")
            self.recruit_url = pdf_data.get("recruitUrl", "채용 공고 URL이 없습니다.")
        
        # 세션 초기화
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
        
        print(f"새로운 세션 생성 완료: {token}")
        
        self.llm = OpenAI(api_key=API_KEY)

    def get_current_state(self):
        return {
            "total_main": len(self.main_questions),
            "current_main": self.current_main,
            "current_follow_up": self.current_follow_up,
            "current_answer": self.current_answer,
            "remaining_answer": self.answer_per_question - self.current_answer,
        }

    def _load_mock_interview_data(self, mock_data_path=None):
        """모의 면접 데이터를 로드하는 메서드"""
        if not mock_data_path:
            mock_data_path = os.path.join(FILE_DIR, "mock_interview_data.json")
        
        try:
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

    #대표질문 생성
    async def generate_main_questions(self, num_questions: int = 5):
        """여러 개의 대표 질문을 생성하는 메서드"""
        try:
            questions = []
            print(f"대표 질문 생성 시작 - 목표 개수: {num_questions}")
            
            for i in range(num_questions):
                print(f"📝 {i+1}번째 질문 생성 시도 중...")
                question = await self.generate_main_question()
                
                if question:
                    questions.append(question)
                    print(f"✅ {i+1}번째 질문 생성 성공: {question}")
                else:
                    print(f"❌ {i+1}번째 질문 생성 실패")
                    break
            
            if not questions:
                print("❌ 생성된 질문이 없습니다.")
                return ["대표질문을 생성할 수 없습니다. 잠시 후 다시 시도해주세요."] * num_questions
            
            print(f"✅ 총 {len(questions)}개의 질문 생성 완료")
            print(f"생성된 질문 목록: {questions}")
            return questions
            
        except Exception as e:
            print(f"❌ 질문 생성 중 오류 발생: {str(e)}")
            return ["대표질문을 생성할 수 없습니다. 잠시 후 다시 시도해주세요."] * num_questions

    async def generate_main_question(self):
        try:
            if len(self.main_questions) >= self.question_num:
                print("❌ 최대 질문 수에 도달했습니다.")
                return None
            
            print("📝 프롬프트 생성 중...")
            prompt = PromptTemplate(
                template=self._get_question_template(),
                input_variables=['resume', 'job_url']
            )
            chain = LLMChain(prompt=prompt, llm=self.llm)

            # 최대 3번까지 시도
            max_attempts = 3
            for attempt in range(max_attempts):
                print(f"🤖 OpenAI API 호출 중... (시도 {attempt + 1}/{max_attempts})")
                question = chain.run({
                    'resume': self.resume,
                    'job_url': self.recruit_url
                })
                print(f"📄 API 응답: {question}")
                
                # 질문 형식 검증 및 정제
                if not question:
                    print("❌ 질문이 생성되지 않았습니다.")
                    continue
                
                # "질문:" 부분 제거하고 실제 질문만 추출
                question = question.strip()
                if "질문:" in question:
                    question = question.split("질문:")[1].strip()
                    print(f"✅ 질문 추출 완료: {question}")
                else:
                    print("⚠️ '질문:' 형식이 없습니다.")
                    continue
                
                if not question:
                    print("❌ 질문이 비어있습니다.")
                    continue

                # 중복 체크
                is_duplicate = False
                for existing_question in self.main_questions:
                    # 유사도 체크 (단순 문자열 포함 여부)
                    if question in existing_question or existing_question in question:
                        print(f"⚠️ 중복된 질문 감지: {question}")
                        is_duplicate = True
                        break
                
                if is_duplicate:
                    continue

                # DB에 저장
                print("💾 DB 저장 시도 중...")
                db = SessionLocal()
                try:
                    # 세션 ID를 가져오기 위해 InterviewSessionDB 조회
                    session = db.query(InterviewSessionDB).filter_by(session_token=self.token).first()
                    if not session:
                        print(f"❌ 세션을 찾을 수 없습니다: {self.token}")
                        continue
                    
                    new_question = MainQuestionDB(
                        session_id=session.id,  # 세션 ID 사용
                        content=question
                    )
                    db.add(new_question)
                    db.commit()
                    db.refresh(new_question)
                    
                    # 메모리에 질문 추가
                    self.main_questions.append(question)
                    print(f"✅ 질문 생성 성공: {question}")
                    
                    return question
                    
                except Exception as db_error:
                    print(f"❌ DB 저장 중 오류 발생: {str(db_error)}")
                    db.rollback()
                    continue
                finally:
                    db.close()
            
            print("❌ 유효한 질문을 생성하지 못했습니다.")
            return None
            
        except Exception as e:
            print(f"❌ 질문 생성 중 오류 발생: {str(e)}")
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
                # 현재 세션의 메인 질문을 가져옴
                session = db.query(InterviewSessionDB).filter_by(session_token=self.token).first()
                if not session:
                    print(f"❌ 세션을 찾을 수 없습니다: {self.token}")
                    return question
                
                # 현재 메인 질문 인덱스에 해당하는 질문을 가져옴
                main_questions = db.query(MainQuestionDB).filter_by(session_id=session.id).all()
                if not main_questions or self.current_main >= len(main_questions):
                    print(f"❌ 메인 질문을 찾을 수 없습니다: 인덱스 {self.current_main}")
                    return question
                
                main_question = main_questions[self.current_main]
                
                new_follow_up = FollowUpDB(
                    session_id=main_question.session_id,
                    main_question_id=main_question.id,
                    content=question
                )
                db.add(new_follow_up)
                db.commit()
                db.refresh(new_follow_up)
                
                # 메모리에도 저장
                self.follow_up_questions[self.current_main].append(question)
                return question
                
            except Exception as e:
                print(f"❌ DB 저장 중 오류 발생: {str(e)}")
                db.rollback()
                return question
            finally:
                db.close()

        except Exception as e:
            print(f"꼬리질문 생성 중 오류 발생: {str(e)}")
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

            self.feedbacks[self.current_main].append(feedback)
            return feedback
        except Exception as e:
            print(f"피드백 생성 중 오류 발생: {str(e)}")
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
        1. 한국어로 작성
        2. 이력서와 채용 공고에 맞는 구체적인 질문
        3. 예시 질문과 비슷한 스타일로 작성
        4. "질문: ~" 형식으로 작성
        5. 추가 설명 없이 질문만 작성
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

    def _get_hint_template(self):
        return '''
        다음 이력서와 면접 질문을 바탕으로 답변 힌트를 생성해주세요.

        [이력서]
        {resume}

        [면접 질문 {question_index}]
        {question}

        다음 형식으로 힌트를 작성해주세요:
        1. 핵심 키워드: (답변에 꼭 포함되어야 할 3-4개의 키워드)
        2. STAR 기법 적용 방향:
           - Situation: (상황 설명 방향)
           - Task: (과제/목표 설명 방향)
           - Action: (행동 설명 방향)
           - Result: (결과 설명 방향)
        3. 구체적인 수치/데이터 제안: (가능한 경우)
        4. 차별화 포인트: (다른 지원자와 차별화할 수 있는 답변 방향)
        '''

    def _get_feedback_template(self):   # 피드백 생성 프롬프트 템플릿
        return f'''
        [Evaluation Rubric]
        - 명확성: 1~5점
        - 관련성: 1~5점 
        - 구체성: 1~5점
        - 전문성: 1~5점

        [Answer Analysis]
        {{answer}}

        [Feedback Requirements]
        1. 각 평가 항목별 점수 및 근거
        2. 개선을 위한 액션 아이템 3개
        3. 모범 답안 예시 포함
        4. GPT-4 Turbo의 1750 토큰 제한 내에서 완결성 있는 응답
        '''
