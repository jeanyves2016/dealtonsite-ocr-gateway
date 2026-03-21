@app.post("/ocr")
async def ocr(file: UploadFile = File(...)):
    file_id = str(uuid.uuid4())

    input_path = f"/tmp/{file_id}_{file.filename}"
    output_path = f"{OUTPUT_DIR}/ocr_{file_id}.pdf"

    # ✅ sauvegarde fichier
    with open(input_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    # ✅ conversion image → PDF
    if input_path.lower().endswith((".png", ".jpg", ".jpeg")):
        image = Image.open(input_path).convert("RGB")
        pdf_input_path = input_path + ".pdf"
        image.save(pdf_input_path)
        input_path = pdf_input_path

    # ✅ OCR
    try:
        subprocess.run([
            "ocrmypdf",
            "--force-ocr",
            input_path,
            output_path
        ], check=True)
    except subprocess.CalledProcessError as e:
        print("OCR ERROR:", e)
        return {"status": "error", "message": "OCR failed"}

    # ✅ extraction texte
    try:
        extracted_text = extract_text(output_path)
    except Exception as e:
        print("TEXT ERROR:", e)
        extracted_text = "Extraction texte échouée"

    fields = extract_fields(extracted_text)

    # ✅ Excel
    excel_path = f"{OUTPUT_DIR}/ocr_{file_id}.xlsx"
    df = pd.DataFrame([fields if fields else {"text": extracted_text[:2000]}])
    df.to_excel(excel_path, index=False)

    # ✅ Word
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