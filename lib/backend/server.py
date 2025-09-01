#!/usr/bin/env python3

from fastapi import FastAPI, UploadFile, File
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from typing import List
import io
import zipfile
#from PyPDF2 import PdfMerger  # exemplo de módulo PyPI para juntar PDFs
from convert_stream import DocumentPdf, CollectionPagePdf, PdfStream, PageDocumentPdf



app = FastAPI()


# Habilitar CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # ou ["http://127.0.0.1:35277"] se quiser restringir
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ===================== ROTA DIVIDIR PDF =====================
@app.post("/uploads/pdfs/split")
async def split_pdf(files: List[UploadFile] = File(...)):
    
    print('Adicionando arquivos PDFs')
    pages: list[PageDocumentPdf] = []
    for file_pdf in files:
        current_bytes = await file_pdf.read()
        doc = DocumentPdf.create_from_bytes(io.BytesIO(current_bytes))
        pages.extend(doc.to_pages())
        del doc
        
    # Criar um ZIP em memória
    zip_buffer = io.BytesIO()
    print('Gravando arquivos')
    with zipfile.ZipFile(zip_buffer, "w") as zipf:
        for i, page in enumerate(pages):
            current_doc = DocumentPdf.create_from_pages([page])
            current_bytes = current_doc.to_bytes()
            zipf.writestr(f"page_{i+1}.pdf", current_bytes.getvalue())
            del current_doc
            del current_bytes        
    zip_buffer.seek(0)
    print('Enviando resposta')
    return StreamingResponse(
        zip_buffer,
        media_type="application/zip",
        headers={"Content-Disposition": "attachment; filename=paginas_divididas.zip"},
    )


@app.post("/uploads/pdfs/join")
async def join_pdfs(files: List[UploadFile] = File(...)):
    #merger = PdfMerger()
    collection_pages = CollectionPagePdf()
    stream = PdfStream()
    
    for file in files:
        pdf_bytes = await file.read()
        #merger.append(io.BytesIO(pdf_bytes))
        _doc = DocumentPdf.create_from_bytes(io.BytesIO(pdf_bytes))
        collection_pages.add_pages(_doc.to_pages())
        del _doc

    new_doc = DocumentPdf.create_from_pages(collection_pages.pages)
    # Salvar em memória
    #output_stream = io.BytesIO()
    #merger.write(output_stream)
    #merger.close()
    #output_stream.seek(0)

    # Retornar como resposta HTTP
    return StreamingResponse(
        new_doc.to_bytes(),
        media_type="application/pdf",
        headers={"Content-Disposition": "attachment; filename=resultado.pdf"}
    )
