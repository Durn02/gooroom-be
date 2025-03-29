# 공식 Python 이미지 사용
FROM python:3.10

# Poetry 설치
RUN pip install --no-cache-dir poetry

# 의존성 설치용 디렉토리
WORKDIR /deps

# pyproject.toml과 poetry.lock 복사
COPY pyproject.toml poetry.lock /deps/

# Poetry로 의존성 설치 (가상 환경 비활성화)
RUN poetry config virtualenvs.create false \
    && poetry install --no-interaction --no-ansi --no-root

# 애플리케이션 디렉토리
WORKDIR /

# PYTHONPATH에 /deps와 /app 추가
ENV PYTHONPATH=/deps/lib/python3.10/site-packages

# 포트 노출
EXPOSE 8000