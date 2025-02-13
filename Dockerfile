FROM python:3.9-slim

WORKDIR /app

COPY requirements.txt requirements.txt
COPY chaesiktak_llm.py chaesiktak_llm.py
COPY templates/ templates/
COPY vegetarian_substitutes_translated.xlsx vegetarian_substitutes_translated.xlsx
COPY chaesiktak_prompt.txt chaesiktak_prompt.txt

RUN pip install --no-cache-dir -r requirements.txt

CMD ["python", "chaesiktak_llm.py"]

EXPOSE 5000