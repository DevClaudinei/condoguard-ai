# Imagem de inferência do CondoGuard (FastAPI + Sentence-Transformers).
FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    HF_HOME=/opt/models \
    SENTENCE_TRANSFORMERS_HOME=/opt/models \
    TRANSFORMERS_OFFLINE=0

WORKDIR /app

# requirements.txt está em UTF-16; converte para UTF-8 antes do pip (pip espera UTF-8).
COPY requirements.txt ./requirements.txt
RUN python -c "data=open('requirements.txt','rb').read(); \
open('requirements.txt','w',encoding='utf-8').write(data.decode('utf-16') if data[:2] in (b'\xff\xfe', b'\xfe\xff') else data.decode('utf-8'))" \
    && pip install --no-cache-dir -r requirements.txt

# Baixa o modelo no build; em runtime o classifier usa local_files_only=True.
RUN python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('all-MiniLM-L6-v2')"

COPY app ./app
COPY migrations ./migrations
COPY scripts ./scripts

EXPOSE 8000

# 1 worker por task: evita N cópias do modelo Sentence-Transformers na RAM.
# A escala é horizontal — via desired_count/Auto Scaling de tasks do ECS Fargate.
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
