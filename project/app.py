from flask import Flask, request, render_template, jsonify
import pandas as pd
import json
import os
import re
from langchain.chat_models import ChatOpenAI
from langchain.schema import HumanMessage
from langchain.vectorstores import FAISS
from langchain.embeddings.openai import OpenAIEmbeddings
from langchain.text_splitter import CharacterTextSplitter
from langchain.chains import RetrievalQA
from langchain.prompts import PromptTemplate
from langchain.llms import OpenAI

app = Flask(__name__)

# OpenAI API Key 설정
os.environ["OPENAI_API_KEY"] = "myapikey"

# 엑셀 파일 로드
file_path = "vegetarian_substitutes_translated.xlsx"
df = pd.read_excel(file_path)

# 채식 대체 식재료 매핑
substitutes_dict = {
   row["동물성 식재료"].strip().lower(): row["채식 대체 식품"].strip()
   for _, row in df.iterrows()
}

# ✅ 1. FAISS를 이용한 벡터 DB 생성 (검색 최적화)
documents = [f"{row['동물성 식재료']} -> {row['채식 대체 식품']}" for _, row in df.iterrows()]

# 벡터 변환
text_splitter = CharacterTextSplitter(chunk_size=100, chunk_overlap=20)
docs = text_splitter.create_documents(documents)
embeddings = OpenAIEmbeddings()
vectorstore = FAISS.from_documents(docs, embeddings)

# ✅ 2. 검색 최적화: 상위 3개 문서만 검색하도록 설정
retriever = vectorstore.as_retriever(search_kwargs={"k": 3})

# ✅ 3. 프롬프트 템플릿 적용 (한 번의 호출로 모든 분석 수행)
prompt_template = PromptTemplate(
   template=(
      """당신은 영양학 전문가이자 채식 식단 분석가입니다.
      다음은 동물성 식재료를 대체한 채식 구성입니다:
      {output_json}은 동물성 식재료를 대체한 채식 구성이고,
      {input_json}은 동물성 식재료 대체 전 재료 구성입니다.
      
      지금 기존 재료에서 대체 재료를 추천하는 상황입니다.
      이 상황에 맞춰서
      {input_json}과 {output_json}을 서로 비교하여 음식 구성이 영양적으로 균형 잡혔는지 평가하고,
      대체 식품으로 {output_json}을 추천하는 이유를 채식 식단의 장점으로 설명하는 내용이 들어가도록
      분석 결과를 바탕으로 간결한 한글 문장으로 출력해 주세요.

      {input_json}과 {output_json} 안에 위치한 "\" 문자를 제거한 뒤 출력하세요.
      
      input_json은 영어로 구성되어 있지만 출력 결과는 전부 한글로 해야 합니다.
      친절한 의사가 환자한테 말하는 어투로 합니다.
      
      기존 대체 재료를 작성하지 않고 매칭된 채식 식재료들만 문장 형태로 보여줍니다.
      줄바꿈 문자 '\\n', '\\'를 포함하지 않고 한 줄로 출력하세요.
      
      이렇게 바꾸면 채식 구성으로도 맛과 영양 모두 챙길 수 있으니 바꾸는걸 추천드려요 와 같은 어투."""
   ),
   input_variables=["input_json", "output_json"]
)

# HTML 렌더링
@app.route('/')
def index():
   return render_template("index.html")

# JSON 데이터 처리 API
@app.route('/convert', methods=['POST'])
def convert():
   data = request.get_json()

   if not data or "counts" not in data:
      return jsonify({"error": "Invalid input JSON"}), 400

   # 동물성 식재료 대체 리스트 매칭
   output_dict = {
      key: substitutes_dict[key] for key in data["counts"] if key in substitutes_dict
   }

   return jsonify(output_dict)

# ✅ 4. 최적화된 OpenAI API 호출 (한 번만 호출)
@app.route('/recommend', methods=['POST'])
def recommend():
   data = request.get_json()

   if not data or "counts" not in data:
      return jsonify({"error": "Invalid input JSON"}), 400

   input_json = json.dumps(data["counts"], ensure_ascii=False)

   # 벡터 검색 수행 (최적화된 retriever 사용)
   retrieved_docs = retriever.get_relevant_documents(input_json)
   retrieved_text = " ".join([doc.page_content for doc in retrieved_docs])

   # 프롬프트에 데이터 적용
   prompt = prompt_template.format(
      input_json=input_json,
      output_json=retrieved_text
   )

   # OpenAI를 한 번만 호출하여 모든 분석 수행 (비용 절감)
   chat = ChatOpenAI(model_name="gpt-3.5-turbo-16k")
   response = chat([HumanMessage(content=prompt)])

   # ✅ 텍스트 정리 (줄바꿈 문자, 역슬래시, 특수문자 제거)
   cleaned_text = re.sub(r"[\\\n\r\t]", " ", response.content)  # \, \n, \r, \t 제거
   cleaned_text = re.sub(r"\s+", " ", cleaned_text).strip()  # 연속된 공백 제거


   return jsonify({"recommendation": cleaned_text})

if __name__ == '__main__':
   app.run(host='0.0.0.0', port=5000)
