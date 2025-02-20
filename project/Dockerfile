# Python 기반 이미지 사용
FROM python:3.9

# 작업 디렉토리 설정
WORKDIR /project

# 필요한 파일 복사
COPY . /project

# 패키지 설치
RUN pip install --no-cache-dir -r requirements.txt

# Flask 앱 실행
CMD ["python", "app.py"]
