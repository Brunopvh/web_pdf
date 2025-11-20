#!/usr/bin/env python3
"""
    
"""
from __future__ import annotations
import os
import sys
from fastapi import FastAPI, UploadFile, File
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi import UploadFile, File
from fastapi.responses import JSONResponse
from fastapi import Form
import base64
from typing import Any
import uuid

import io
import zipfile
import convert_stream as cs
import ocr_stream as ocr
import soup_files as sp
import pandas as pd
import tempfile
import threading
import shutil
from sheet_stream import ListItems

# Script principal -> backend/server.py
SERVER_FILE = os.path.abspath(os.path.realpath(__file__)) 
# Diretório library -> backend/library
DIR_SERVER_LIBRARY = os.path.abspath(os.path.join(os.path.dirname(SERVER_FILE), 'library'))
# backend/organize_stream
DIR_MOD_ORGANIZE = os.path.abspath(os.path.join(os.path.dirname(SERVER_FILE), 'organize_stream'))
# Diretório raiz do projeto web_convert
DIR_OF_PROJECT = os.path.abspath(os.path.join(DIR_SERVER_LIBRARY, '..', '..')) 
DIR_ASSETS = os.path.join(DIR_OF_PROJECT, 'frontend', 'assets', 'data')
FILE_CONF = os.path.join(DIR_ASSETS, 'ips.json')
sys.path.insert(0, DIR_SERVER_LIBRARY)
sys.path.insert(0, DIR_MOD_ORGANIZE)


from organize_stream.type_utils import (
    FilterText, FilterData, LibDigitalized
)
from organize_stream.document.create_name import (
    CreateNewFile, ExtractNameInnerData, ExtractNameInnerText,
    DiskFileInfo, DiskOriginInfo, DiskOutputInfo,
)
from sheet_stream import ReadFileSheet, LibSheet

from organize_stream.library.common import (
    get_json_info, get_temp_dir 
)
from organize_stream.library.progress_route import (
    create_progress_with_id, thread_images_to_pdfs, TASK_PROGRESS_STATE, router as progress_router,
    get_id_progress_state, get_json_progress, thread_organize_documents
)

TESS_FILE: str | None = None
if sp.KERNEL_TYPE == 'Linux':
    TESS_FILE = '/usr/bin/tesseract'
    if not os.path.exists(TESS_FILE):
        raise FileNotFoundError(f'Arquivo não encontrado: {TESS_FILE}')
elif sp.KERNEL_TYPE == 'Windows':
    TESS_FILE = shutil.which('tesseract.exe')
if TESS_FILE is None:
    raise FileNotFoundError(
        f'tesseract.exe não encontrado em PATH, instale o tesseract ou defina um valor para TESS_FILE em {__file__}'
    )    

    
app = FastAPI()

# Habilitar CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


route_info: dict[str, Any] = get_json_info(sp.File(FILE_CONF))
if route_info is None:
    print(f'Erro: a rota está vazia, verifique o JSON de rotas')
    sys.exit(1)
print(route_info)

# =============== INCLUIR ROTAS MODULARIZADAS ==================
app.include_router(progress_router, prefix="") # Inclui o roteador de progresso


# =============== ROTA DOWNLOAD ==================
@app.get("/download/{task_id}")
async def download_result(task_id: str):
    # Busca o estado da tarefa pelo ID
    current_progress: dict[str, Any] = get_id_progress_state(task_id)
    if current_progress is None:
        return JSONResponse({"error": "Barra de progresso inválida ou vazia."}, status_code=400)
    
    if (not current_progress["done"]) or (not current_progress["zip_path"]):
        return JSONResponse({"error": "Arquivo ainda não está pronto"}, status_code=400)

    print(f'Baixando: {current_progress["zip_path"]}')
    zip_path = current_progress["zip_path"]
    
    # Após o download, remove a tarefa do dicionário global para limpeza
    if task_id in TASK_PROGRESS_STATE:
        del TASK_PROGRESS_STATE[task_id]
        
    return StreamingResponse(
        open(zip_path, "rb"),
        media_type="application/zip",
        headers={"Content-Disposition": "attachment; filename=result.zip"},
    )


# 01 =================== ROTA PARA OCR EM IMAGENS =====================
@app.post(f"/{route_info['rt_ocr']}")
async def ocr_images(
            files: list[UploadFile] = File(...),
        ):
    """
        Aplica OCR em imagens enviadas e retorna um ZIP com os PDFs resultantes.
    """
    zip_buffer = io.BytesIO()
    recognize_img = ocr.RecognizeImage(
        ocr.BinTesseract(File(TESS_FILE))
    )
    with zipfile.ZipFile(zip_buffer, "w") as zipf:
        for i, file in enumerate(files):
            content = await file.read()
            image = cs.ImageObject.create_from_bytes(content)
            doc_pdf = recognize_img.image_recognize(image).to_document()
            zipf.writestr(f"ocr_documento_{i + 1}.pdf", doc_pdf.to_bytes().getvalue())
            del doc_pdf
    zip_buffer.seek(0)

    return StreamingResponse(
        zip_buffer,
        media_type="application/zip",
        headers={"Content-Disposition": "attachment; filename=ocr_documents.zip"},
    )


# 02 ===================== ROTA PDF PARA IMAGENS =====================
@app.post(f"/{route_info['rt_convert_pdf']}")
async def convert_pdfs(files: list[UploadFile] = File(...)):
    """
        Rota para converter PDFs em imagens
    """
    final_list_imgs: list[cs.ImageObject] = []
    for file in files:
        file_bytes = await file.read()
        tmp_doc = cs.DocumentPdf(io.BytesIO(file_bytes))
        conv_pdf_to_images = cs.ConvertPdfToImages.create(tmp_doc)
        current_imgs: list[cs.ImageObject] = conv_pdf_to_images.to_images()
        final_list_imgs.extend(current_imgs)
        current_imgs.clear()
        del tmp_doc
        del conv_pdf_to_images
    
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w") as zipf:
        # Compactar as imagens da lista em formato zip.
        for n, img in enumerate(final_list_imgs):
            _bytes_img: bytes = img.to_bytes().getvalue()
            zipf.writestr(f"imagem_{n + 1}.png", _bytes_img)
            del _bytes_img 
    final_list_imgs.clear()
    del final_list_imgs
    zip_buffer.seek(0)
    return StreamingResponse(
        zip_buffer,
        media_type="application/zip",
        headers={"Content-Disposition": "attachment; filename=pdf-para-imagens.zip"},
    )


# 03 ===================== ROTA DIVIDIR PDF =====================
@app.post(f"/{route_info['rt_split_pdf']}")
async def split_pdf(files: list[UploadFile] = File(...)):
    """
        Recebe uma lista de arquivos PDFs, converte cada página de cada
    PDF será convertida em arquivo PDF individual.
    """
    pages: list[cs.PageDocumentPdf] = []
    for file_pdf in files:
        current_bytes = await file_pdf.read()
        doc = cs.DocumentPdf(io.BytesIO(current_bytes))
        pages.extend(doc.to_pages())
        del doc

    # Criar um ZIP em memória
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w") as zipf:
        for i, page in enumerate(pages):
            current_doc = cs.DocumentPdf.create_from_pages([page])
            current_bytes = current_doc.to_bytes()
            zipf.writestr(f"pag_{i + 1}.pdf", current_bytes.getvalue())
            del current_doc
            del current_bytes

    zip_buffer.seek(0)
    return StreamingResponse(
        zip_buffer,
        media_type="application/zip",
        headers={"Content-Disposition": "attachment; filename=paginas_divididas.zip"},
    )


# 04 ===================== ROTA JUNTAR PDF =====================
@app.post(f"/{route_info['rt_join_pdf']}")
async def join_pdfs(files: list[UploadFile] = File(...)):
    """
        Recebe uma lista de arquivos PDF e junta tudo em arquivo único.
    """
    # Nome do arquivo a ser baixado.
    output_filename = 'Documento-juntado.pdf'
    collection_pages: cs.CollectionPagePdf = cs.CollectionPagePdf([])

    for file in files:
        pdf_bytes: bytes = await file.read()
        _doc = cs.DocumentPdf(io.BytesIO(pdf_bytes))
        collection_pages.add_pages(_doc.to_pages())
        del _doc
    new_doc = cs.DocumentPdf.create_from_pages(collection_pages)
    # Retornar como resposta HTTP
    return StreamingResponse(
        new_doc.to_bytes(),
        media_type="application/pdf",
        headers={"Content-Disposition": "attachment; filename={}".format(output_filename)}
    )


# 05 =============== CONVERTER IMAGENS EM PDF ===============
@app.post(f"/{route_info['rt_imgs_to_pdf']}")
async def process_images(files: list[UploadFile] = File(...)):
    # 1. Gera um ID único para esta tarefa
    task_id = str(uuid.uuid4())
    # 2. Inicializa o estado de progresso para este ID
    create_progress_with_id(task_id)
    
    image_files: list[str] = []

    # Salvar os uploads em arquivos temporários
    for upload in files:
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".jpg")
        content: bytes = await upload.read()
        temp_file.write(content)
        temp_file.close()
        image_files.append(temp_file.name)
    # Rodar conversão em thread
    thread = threading.Thread(target=thread_images_to_pdfs, args=(image_files, task_id))
    thread.start()
    return {"message": "Processamento iniciado", "task_id": task_id}


# ===================== ROTA UNIFICADA PROCESSAR DOCUMENTOS =====================

@app.post(f"/{route_info['rt_process_docs']}")
async def organize_documents_with_sheet(
            pdfs: list[UploadFile] = File(default=[]),
            images: list[UploadFile] = File(default=[]),
            file_sheet: UploadFile = File(default=None),
            column_name: str = Form(default=None),  # NOVO
        ):
    """
    Rota unificada para processar PDFs, imagens e renomear com base em uma planilha Excel.
    """
    progress_data = create_progress_with_id()

    temp_dir: str = tempfile.mkdtemp()
    progress_data.update({"current": 0, "total": 0, "done": False, "zip_path": None})
    list_files: list[UploadFile] = []
    list_files.extend(pdfs)
    list_files.extend(images)
    sheet_bytes: bytes = await file_sheet.read()
    src_df: pd.DataFrame = ReadFileSheet(io.BytesIO(sheet_bytes), lib_sheet=LibSheet.EXCEL).get_dataframe()
    try:
        # Salvar todos os arquivos recebidos
        saved_files: list[str] = []
        for current_file in list_files:
            if current_file is None:
                continue
            content: bytes = await current_file.read()
            file_path: str = os.path.join(temp_dir, current_file.filename)
            with open(file_path, "wb") as f:
                f.write(content)
            saved_files.append(file_path)
        total_files = len(saved_files)
        progress_data["total"] = total_files
        
        src_dir: sp.Directory = sp.Directory(temp_dir)
        input_files = sp.InputFiles(src_dir)
        __files_pdf = input_files.pdfs
        __files_images = input_files.images
        filter_data = FilterData(
            src_df, col_find=column_name, col_new_name=column_name, cols_in_name=[]
        )
        name_finder = ExtractNameInnerData(src_dir, filters=filter_data)
        for img in __files_images:
            name_finder.add_table(
                name_finder.extractor.read_image(img)
            )
        for file_pdf in __files_pdf:
            name_finder.add_table(
                name_finder.extractor.read_document(file_pdf)
            )
        progress_data.update({"done": True})
        
        # Gerar uma lista de arquivos PDF
        docs_list: list[sp.File] = input_files.pdfs
        # Gerar uma lista de imagens.
        docs_imgs: list[sp.File] = input_files.images
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, "w") as zipf:
            for file_pdf in docs_list:
                _pdf_bytes: bytes = file_pdf.path.read_bytes()
                zipf.writestr(file_pdf.basename(), _pdf_bytes)
                
            for file_img in docs_imgs:
                _img_bytes: bytes = file_img.path.read_bytes()
                zipf.writestr(file_img.basename(), _img_bytes)
        zip_buffer.seek(0)

        # Retornar o ZIP finalizado
        return StreamingResponse(
            zip_buffer,
            media_type="application/zip",
            headers={"Content-Disposition": "attachment; filename=filtrado_com_tabela.zip"},
        )

    except Exception as e:
        progress_data.update({"done": True, "zip_path": None})
        print(f"[ERRO] Falha ao processar documentos: {e}")
        return JSONResponse({"error": str(e)}, status_code=500)


@app.post(f"/{route_info['rt_process_pattern']}")
async def organize_documents_with_pattern(
            pdfs: list[UploadFile] = File(default=[]),
            images: list[UploadFile] = File(default=[]),
            pattern: str = Form(default=None), 
            document_type: str = Form(default=None),
        ):
    """
    Rota alternativa usada quando o usuário digita um padrão de texto
    ao invés de enviar planilha XLSX e nome de coluna.
    Retorna um ZIP com os arquivos processados.
    """
    if not pattern:
        if not document_type:
            e = "O parâmetro 'pattern' é obrigatório nesta rota."
            return JSONResponse({"error": str(e)}, status_code=500)

    task_id = str(uuid.uuid4())
    progress_data = create_progress_with_id(task_id)
    progress_data.update({"current": 0, "total": 0, "done": False, "zip_path": None})
    total_files = len(images) + len(pdfs)
    progress_data['total'] = total_files
    
    input_files_image: ListItems[DiskOriginInfo] = ListItems()
    input_files_pdf: ListItems[DiskOriginInfo] = ListItems()
    
    # Imagens
    image_file: UploadFile
    for image_file in images:
        if image_file is None:
            continue
        current = DiskOriginInfo()
        extension_file = f".{image_file.filename.split('.')[-1]}"
        image_bytes: bytes = await image_file.read()
        current.set_file_bytes(image_bytes)
        current.set_filename(image_file.filename)
        current.set_extension(extension_file)
        input_files_image.append(current)
        
    progress_data['current'] = total_files / 2
    for file_pdf in pdfs:
        if file_pdf is None:
            continue
        current = DiskOriginInfo()
        extension_file = f".{file_pdf.filename.split('.')[-1]}"
        pdf_bytes: bytes = await file_pdf.read()
        current.set_file_bytes(pdf_bytes)
        current.set_filename(file_pdf.filename)
        current.set_extension(extension_file)
        input_files_pdf.append(current)
        
    send_args: dict[str, object] = {
        'task_id': task_id,
        'images': input_files_image,
        'pdfs': input_files_pdf,
        'pattern': pattern,
        'document_type': document_type,
    }
    progress_data["total"] = total_files
    thread = threading.Thread(target=thread_organize_documents, kwargs=send_args)
    thread.start()
    return {"message": "Processamento iniciado", "task_id": task_id}



