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

            question = chain.run({
                'resume': self.resume,
                'job_url': self.recruit_url
            }).strip()
            
            if "질문:" in question:
                question = question.split("질문:")[1].strip()
            
            # 🔥 수정됨: 생성된 질문을 DB에 저장하도록 변경
            db = SessionLocal()
            try:
                session = db.query(InterviewSessionDB).filter_by(session_token=self.token).first()
                if not session:
                    print(f"❌ 세션을 찾을 수 없습니다: {self.token}")
                    return None
                
                new_question = ChatMessageDB(
                    session_id=session.id,
                    message_type="main_question",  # 메인 질문 타입 지정
                    content=question
                )
                db.add(new_question)
                db.commit()
                db.refresh(new_question)
                
                self.main_questions.append(question)
                print(f"✅ 질문 생성 성공: {question}")
                
                return question
                    
            except Exception as db_error:
                print(f"❌ DB 저장 중 오류 발생: {str(db_error)}")
                db.rollback()
            finally:
                db.close()
            
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
            finally:
                db.close()

            return question
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

     