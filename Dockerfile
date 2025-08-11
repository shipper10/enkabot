
FROM python:3.11-slim
ENV DEBIAN_FRONTEND=noninteractive
WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends \ 
    build-essential \ 
    python3-dev \ 
    pkg-config \ 
    libcairo2 \ 
    libcairo2-dev \ 
    libpango-1.0-0 \ 
    libpango1.0-dev \ 
    libpangocairo-1.0-0 \ 
    libgdk-pixbuf2.0-0 \ 
    libffi-dev \ 
    libjpeg-dev \ 
    libfreetype6 \ 
    libfreetype6-dev \ 
    fonts-dejavu-core \ 
    fonts-noto-cjk \ 
    fonts-noto-color-emoji \ 
    fonts-noto-core \ 
    fonts-noto-extra \ 
    fonts-noto-ui-core \ 
    && rm -rf /var/lib/apt/lists/*
COPY requirements.txt /app/requirements.txt
RUN pip install --upgrade pip
RUN pip install --no-cache-dir -r /app/requirements.txt
COPY . /app
EXPOSE 8080
CMD ["python", "genshin_postgres_enka_local.py"]
