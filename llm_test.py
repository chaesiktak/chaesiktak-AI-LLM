import json
import pandas as pd
from openai import OpenAI


# ❗❗❗api Key. git 커밋 전 꼭 꼭 확인 ❗❗❗
client = OpenAI(api_key = '')

file_path = "vegetarian_alternative_list.xlsx"  # 채식 재료 매칭 리스트
df = pd.read_excel(file_path)

with open("chaesiktak_prompt.txt", "r", encoding="utf-8") as file:
    prompt_template = file.read()  # 프롬프트 파일

# 소문자 변환
substitutes_dict = {
    row["동물성 식재료"].strip().lower(): row["채식 대체 식품"].strip()
    for _, row in df.iterrows()
}

input_json = {
    "counts": {
        "beef": 8,
        "pork": 5,
        "salmon": 10,
        "lettuce": 20,
        "almond": 3,
        "vegetable": 25
    }
}

# 동물성 식재료 대체 리스트 매칭
output_dict = {
    key: substitutes_dict[key] for key in input_json["counts"] if key in substitutes_dict
}

output_json = json.dumps(output_dict, ensure_ascii=False, indent=2)  # 들여쓰기 2칸씩
print(output_json)

prompt = prompt_template.format(output_json=output_json, input_json=input_json)

completion = client.chat.completions.create(
    model="gpt-3.5-turbo-1106",
    messages=[{"role": "user", "content": prompt}]
)

response_text = completion.choices[0].message.content
print(response_text)