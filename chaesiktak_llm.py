from flask import Flask, request, render_template, Response, jsonify
import json
import pandas as pd
from openai import OpenAI
from flask_cors import CORS  # 모든 도메인 허용


def load_api_key():
    with open("open_ai_key.txt", "r", encoding="utf-8") as file:
        return file.read().strip()

API_KEY = load_api_key()
client = OpenAI(api_key = API_KEY)

app = Flask(__name__)
CORS(app)

def load_substitutes():
    file_path = "vegetarian_substitutes_translated.xlsx"
    df = pd.read_excel(file_path)
    return {row["동물성 식재료"].strip().lower(): row["채식 대체 식품"].strip() for _, row in df.iterrows()}  # 딕셔너리 형태 변환 후, 소문자 & 공백 제거

substitutes_dict = load_substitutes()

def load_prompt_template():
    with open("chaesiktak_prompt.txt", "r", encoding="utf-8") as file:
        return file.read()

prompt_template = load_prompt_template()

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/generate', methods=['POST'])
def generate_response():
    try:
        input_json = request.get_json()
        if not input_json or "counts" not in input_json:
            return jsonify({"error": "Invalid JSON format: 'counts' key is missing."}), 400
        
        # 대체 재료 매칭 안된거 제거(excel).
        output_dict = {key: substitutes_dict.get(key, "No substitute found") for key in input_json["counts"]}
        filtered_output_dict = {key: value for key, value in output_dict.items() if value != "No substitute found"}

        output_json = json.dumps(filtered_output_dict, ensure_ascii=False)
        prompt = prompt_template.format(output_json=output_json, input_json=json.dumps(input_json, ensure_ascii=False))

        completion = client.chat.completions.create(
            model="gpt-3.5-turbo-1106",
            messages=[{"role": "user", "content": prompt}]
        )
        response_text = completion.choices[0].message.content
        
        response_text = response_text.strip('"')  # 양끝 큰따옴표 제거
        response_text = response_text.replace("\\", "")  # 백슬래시 제거
        response_text = response_text.replace("\n", " ")  # 줄바꿈 제거
        response_text = response_text.replace("\t", " ")  # 탭 제거
        response_text = response_text.replace('\"', '')  # 문자열 내부의 큰따옴표 제거
        response_text = response_text.strip()  # 앞뒤 공백 제거

        try:
            response_text = json.loads(f'"{response_text}"')
        except json.JSONDecodeError:
            pass  # 오류 발생 시 원래 문자열 유지

        response_data = {
            "response": response_text,
            "output_dict": filtered_output_dict
        }
        return Response(json.dumps(response_data, ensure_ascii=False), mimetype='application/json')

    except json.JSONDecodeError:
        return jsonify({"error": "Invalid JSON format: JSON parsing failed."}), 400
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run('0.0.0.0', port = 5000, debug=True)