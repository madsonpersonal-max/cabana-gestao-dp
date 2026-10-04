FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY api/requisitos.txt ./requirements.txt

RUN pip install --no-cache-dir -r requirements.txt

COPY api/aplicativo ./aplicativo

EXPOSE 8000

CMD ["uvicorn", "aplicativo.main:app", "--host", "0.0.0.0", "--port", "8000"]
