from fastapi import FastAPI, UploadFile, File
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pdfminer.high_level import extract_text
import pandas as pd
from docx import Document
import shutil
import subprocess
import os
import uuid
import re

app = FastAPI(title="Dealtonsite OCR Gateway")

OUTPUT_DIR = "/app/output"
os.makedirs(OUTPUT_DIR, exist_ok=True)

# Servir le frontend
app.mount("/", StaticFiles(directory="app/static", html=True), name="static")


@app.get("/health")
def health():
    return {"status": "ok"}


def extract_fields(text):
    data = {}

    invoice = re.search(r"(facture|invoice)[^\n]*?(\d+)", text, re.IGNORECASE)
    if invoice:
        data["invoice_number"] = invoice.group(2)

    date = re.search(r"\b\d{2}/\d{2}/\d{4}\b", text)
    if date:
        data["date"] = date.group()

    amount = re.search(r"(\d+[.,]?\d*)\s?(FCFA|€|\$)", text)
    if amount:
        data["total_amount"] = amount.group(1)
        data["currency"] = amount.group(2)

    return data


@app.post("/ocr")
async def ocr(file: UploadFile = File(...)):
    file_id = str(uuid.uuid4())

    input_path = f"/tmp/{file_id}_{file.filename}"
    output_path = f"{OUTPUT_DIR}/ocr_{file_id}.pdf"

    with open(input_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    try:
        subprocess.run([
            "ocrmypdf",
            "--force-ocr",
            input_path,
            output_path
        ], check=True)
    except subprocess.CalledProcessError:
        return {"status": "error", "message": "OCR failed"}

    try:
        extracted_text = extract_text(output_path)
    except:
        extracted_text = "Extraction texte échouée"
    fields = extract_fields(extracted_text)

    # Excel
    excel_path = f"{OUTPUT_DIR}/ocr_{file_id}.xlsx"
    df = pd.DataFrame([fields if fields else {"text": extracted_text[:2000]}])
    df.to_excel(excel_path, index=False)

    # Word
    word_path = f"{OUTPUT_DIR}/ocr_{file_id}.docx"
    doc = Document()
    doc.add_heading("OCR Result", 0)
    doc.add_paragraph(extracted_text)
    doc.save(word_path)

    return {
        "status": "success",
        "fields": fields,
        "text_preview": extracted_text[:500],
        "download_pdf": f"/download/{file_id}",
        "download_excel": f"/download/excel/{file_id}",
        "download_word": f"/download/word/{file_id}"
    }


@app.get("/download/{file_id}")
def download_pdf(file_id: str):
    file_path = f"{OUTPUT_DIR}/ocr_{file_id}.pdf"
    return FileResponse(file_path, media_type='application/pdf', filename="ocr_result.pdf")


@app.get("/download/excel/{file_id}")
def download_excel(file_id: str):
    file_path = f"{OUTPUT_DIR}/ocr_{file_id}.xlsx"
    return FileResponse(file_path, filename="result.xlsx")


@app.get("/download/word/{file_id}")
def download_word(file_id: str):
    file_path = f"{OUTPUT_DIR}/ocr_{file_id}.docx"
    return FileResponse(file_path, filename="result.docx")