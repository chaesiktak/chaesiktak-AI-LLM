from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, JSONResponse
import json
import pandas as pd
import redis
from openai import OpenAI
from dotenv import load_dotenv
import os

# 환경 변수 로드
load_dotenv()

# OpenAI API 설정
API_KEY = os.getenv("OPENAI_API_KEY")
client = OpenAI(api_key=API_KEY)

# FastAPI 앱 생성
app = FastAPI()

# 정적 파일 제공 (CSS, JS 포함 가능)
app.mount("/static", StaticFiles(directory="static"), name="static")

# Redis 설정
cache = redis.Redis(host="redis", port=6379, db=0)

# 채식 대체 식재료 데이터 로드
def load_substitutes():
    file_path = "vegetarian_substitutes_translated.xlsx"
    df = pd.read_excel(file_path)
    return {row["동물성 식재료"].strip().lower(): row["채식 대체 식품"].strip() for _, row in df.iterrows()}

substitutes_dict = load_substitutes()

# 프롬프트 템플릿 로드
def load_prompt_template():
    with open("chaesiktak_prompt.txt", "r", encoding="utf-8") as file:
        return file.read()

prompt_template = load_prompt_template()

@app.get("/", response_class=HTMLResponse)
async def read_index():
    file_path = "templates/index.html"
    if os.path.exists(file_path):
        with open(file_path, "r", encoding="utf-8") as file:
            return HTMLResponse(content=file.read())
    return HTMLResponse(content="<h1>index.html 파일을 찾을 수 없습니다.</h1>", status_code=404)

@app.post('/generate')
async def generate_response(data: dict):
    if not data or "counts" not in data:
        raise HTTPException(status_code=400, detail="Invalid JSON format: 'counts' key is missing.")

    output_dict = {key: substitutes_dict.get(key, "No substitute found") for key in data["counts"]}
    filtered_output_dict = {key: value for key, value in output_dict.items() if value != "No substitute found"}

    output_json = json.dumps(filtered_output_dict, ensure_ascii=False)
    prompt = prompt_template.format(output_json=output_json, input_json=json.dumps(data, ensure_ascii=False))

    completion = client.chat.completions.create(
        model="gpt-3.5-turbo-1106",
        messages=[{"role": "user", "content": prompt}]
    )

    response_text = completion.choices[0].message.content.strip()

    response_data = {
        "response": response_text,
        "output_dict": filtered_output_dict
    }
    return JSONResponse(content=response_data)
