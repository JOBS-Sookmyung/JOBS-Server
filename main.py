from fastapi import FastAPI
from openai import OpenAI
import os
from dotenv import load_dotenv

load_dotenv()

app = FastAPI()
client = OpenAI()
client.api_key = os.getenv("OPENAI_API_KEY")

completion = client.chat.completions.create(
    model="gpt-4o-mini",
    messages=[
        {
			"role": "system",
			"content": "You are a helpful assistant. Answer in Korean."
		},
        {
            "role": "user",
            "content": "회계사 합격하는 법 알려줘."
        }
    ]
)

assistantAnswer = completion.choices[0].message.content

@app.get('/')
def home():
	return {"message": "Welcome Home!"}

@app.get('/q')
def question():
	return assistantAnswer
