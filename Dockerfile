FROM python:3.11-slim

WORKDIR /app

# Installer OCRmyPDF + dépendances système
RUN apt-get update && apt-get install -y \
    ocrmypdf \
    tesseract-ocr \
    ghostscript \
    qpdf \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
