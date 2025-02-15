import os
import pandas as pd
from langchain.prompts import PromptTemplate
from langchain.chains import LLMChain
from langchain.llms import OpenAI
from routers import pdf_files
from config import FILE_DIR
from utils.common import load_pdf_to_text, summarize_text, load_mock_interview_data
from config import API_KEY

class InterviewSession:
    def __init__(self, token: str, question_num=5, mock_data_path=None):    # 클래스 초기화 및 템플릿, LLM 체인 설정
        self.token = token
        self.question_num = question_num
        self.question_index = 0
        self.questions = []
        self.answers = []
        self.resume = self._load_pdf_to_resume()
        self.mock_data_path = mock_data_path
        self.example_questions = self._load_mock_interview_data(mock_data_path)

        self.prompt = PromptTemplate(
            template=self._get_question_template(), 
            input_variables=['resume']
            )
        self.llm = OpenAI(api_key=API_KEY)
        self.llm_chain = LLMChain(prompt=self.prompt, llm=self.llm)
    
    
    async def generate_follow_up_question(self, answer):    # 꼬리 질문 생성 함수
        follow_up_prompt = PromptTemplate(
            template=self._get_follow_up_template(),
            input_variables=['answer']
            )
        follow_up_chain = LLMChain(prompt=follow_up_prompt, llm=self.llm)
        return follow_up_chain.arun({'answer': answer})
    
    
    async def generate_hint(self, question):    # 힌트 제공 함수
        hint_prompt = PromptTemplate(
            template=self._get_hint_template(), 
            input_variables=['question']
            )
        hint_chain = LLMChain(prompt=hint_prompt, llm=self.llm)
        return hint_chain.arun({'question': question})


    async def generate_feedback(self, answer: str):   # 피드백 생성 함수
        feedback_prompt = PromptTemplate(
            template=self._get_feedback_template(), 
            input_variables=['answer']
            )
        feedback_chain = LLMChain(prompt=feedback_prompt, llm=self.llm)
        result = await feedback_chain.arun({'answer': answer})
        return result.strip() if result else "피드백을 생성할 수 없습니다."


    def _load_pdf_to_resume(self):
        if self.token not in pdf_files:
            raise ValueError("해당 토큰에 대한 PDF 파일이 존재하지 않습니다.")

        pdf_path = os.path.join(FILE_DIR, f"{self.token}.pdf")
        if not os.path.exists(pdf_path):
            raise FileNotFoundError("PDF 파일이 존재하지 않습니다.")

        pdf_text = load_pdf_to_text(pdf_path)
        summarized_text = summarize_text(pdf_text, max_length=1500)
        return summarized_text


    def _load_mock_interview_data(self, csv_path):
        mock_interview_examples = load_mock_interview_data(csv_path)
        examples_text = "\n".join([f"{i+1}. {example}" for i, example in enumerate(mock_interview_examples)])
        return examples_text


    async def add_answer(self, answer):     # 이게 뭘까??
        self.answers.append(answer)
        recent_qa = "\n".join(  # 최근 5개 질문 - 답변만 유지
        [f"질문 {i+1}: {q}\n답변 {i+1}: {a}" 
        for i, (q, a) in enumerate(zip(self.questions[-5:], self.answers[-5:]))]
        )
        self.resume = f"{self._load_pdf_to_resume()}\n{recent_qa}"


    async def _generate_question(self):
        try:
            result = await self.llm_chain.arun({'resume': self.resume})
            return result.strip() if result else "질문을 생성할 수 없습니다."
        except Exception as e:
            return f"질문 생성 중 오류 발생: {str(e)}"
        

    async def generate_next_question(self, with_hint=False, with_feedback=False, answer=None):
        question_response = await self._generate_question()
        response = {
            "index": self.question_index + 1,
            "question": question_response if isinstance(question_response, str) else question_response.get('question', '질문 없음')
        }

        if with_hint:
            response["hint"] = await self.generate_hint(response["question"])
        if answer:
            response["feedback"] = await self.generate_feedback(answer)
            response["follow_up"] = await self.generate_follow_up_question(answer)
    
        self.questions.append(response["question"])
        self.question_index += 1
        return response

    
    def _get_question_template(self):   # 대표질문 생성 프롬프트 템플릿
        return f'''
        You are an expert AI interviewer.
        Use the following resume to make a question in Korean:
        {{resume}}
        
        Here are example questions from a mock interview dataset:
        {self.example_questions}
        
        The question must:
        1. Be in Korean.
        2. Be specific and tailored to the details of the resume.
        3. Focus on the skills, experiences, or projects mentioned.
        4. Avoid repetition of previously generated questions.
        5. Be similar in style and detail to the examples provided.
        6. Only provide one question at a time.
        7. Be realistic and appropriate for a job interview setting.
        8. Always follow this format: "질문: ~."
        '''
        
    def _get_follow_up_template(self):  # 꼬리질문 생성 프롬프트 템플릿
        return f'''
        You are an expert AI job interviewer.
        Use the following answer from a candidate to create a follow-up question in Korean:
        {{answer}}
        The follow-up question must:
        1. Be in Korean.
        2. Avoid repetition of previously generated questions.
        3. Focus on details mentioned in the answer.
        4. Explore the reasoning, challenges, results, or methodology in the answer.
        5. Only provide one follow-up question at a time.
        6. Always follow this format: "질문: ~."
        '''
    
    def _get_hint_template(self):       # 힌트 생성 프롬프트 템플릿
        return f'''
        You are an expert AI interviewer providing hints.
        Provide a brief hint in Korean to help answer this question effectively:
        질문: {{question}}

        The hint should:
        1. Be concise (1-2 sentences).
        2. Focus on what aspects of experience or skills to highlight.
        3. Be supportive and encouraging.
        4. Use this format: "힌트: ~"
        5. Always include encouraging comments and actionable advice with a kind and supportive tone.
        '''
    
    def _get_feedback_template(self):   # 피드백 생성 프롬프트 템플릿
        return f'''
        You are an expert AI job interview coach. Use the following answer from a candidate to provide detailed feedback in Korean:
        {{answer}}

        The feedback must:
        1. Compliment specific strengths in the answer.
        2. Identify areas where the answer could be more specific or detailed.
        3. Provide concrete examples or suggestions for improvement directly related to the details mentioned in the answer.
        4. Be realistic and appropriate for a professional job interview setting.
        5. Be written in Korean, formatted with clear and professional language.
        6. Always include encouraging comments and actionable advice with a kind and supportive tone.
        Example Feedback:
        "우선, 팀원들의 장점과 관심사를 파악하기 위해 본인이 한 노력의 단계와 과정을 구체적으로 설명하신 부분은 훌륭합니다! 다만 구체적인 경험, 예를 들어 ‘애니를 좋아하는 친구와의 라포를 형성하기 위해 요즘 유행하는 넷플릭스 애니메이션 이름을 언급하며 가까워질 수 있었습니다’와 같은 구체적인 예시가 부족해 보입니다. 다음에는 이런 부분을 언급하면서 답변하면 더욱더 신뢰감을 줄 수 있어 좋을 것으로 보입니다! 👏"
        When giving examples or suggestions, tailor them to the candidate's answer to make them relevant and specific. Avoid reusing generic or unrelated examples.
        Provide the feedback only, without additional explanations or comments.
        '''
    

