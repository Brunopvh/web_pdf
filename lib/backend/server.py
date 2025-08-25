#!/usr/bin/env python3


from fastapi import FastAPI, UploadFile, File
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from typing import List
import io
#from PyPDF2 import PdfMerger  # exemplo de módulo PyPI para juntar PDFs
from convert_stream import DocumentPdf, CollectionPagePdf, PdfStream



app = FastAPI()


# Habilitar CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # ou ["http://127.0.0.1:35277"] se quiser restringir
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
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
