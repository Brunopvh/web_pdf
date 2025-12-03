#!/usr/bin/env python3
"""
    
"""
from __future__ import annotations
import os
import sys

from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi import UploadFile, File, FastAPI
from fastapi.responses import JSONResponse
from fastapi import Form
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

from organize_stream.library.common.assets import (
    get_json_info, get_temp_dir, FILE_PATH_ASSETS, AssetsFrontEnd, BuildAssets
)

# Definir o asset no início para evitar erros de chamadas para este arquivo/objeto.
FILE_PATH_ASSETS = sp.File(FILE_CONF)
app_assets: AssetsFrontEnd = BuildAssets().set_dir_assets(sp.Directory(DIR_ASSETS)).build()
BuildAssets.asset_dir = app_assets.get_dir_assets()


from organize_stream.document.create_name import (
    DictFileInfo, DictOriginInfo, DictOutputInfo,
)
from sheet_stream import ReadFileSheet, LibSheet
from organize_stream.library.progress_route import (
    create_progress_with_id, thread_images_to_pdfs, 
    TASK_PROGRESS_STATE, router as progress_router,
    get_id_progress_state, get_json_progress, thread_organize_documents,
    thread_organize_documents_with_sheet,
)
from organize_stream.library.app_pages.docs_to_sheet import router_docs_to_sheet


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
app.include_router(progress_router, prefix="")
app.include_router(router_docs_to_sheet, prefix="")


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
            column_name: str = Form(default=None),  
        ):
    """
    Rota unificada para processar PDFs, imagens e renomear com base em uma planilha Excel.
    """
    task_id = str(uuid.uuid4())
    progress_data = create_progress_with_id(task_id)

    temp_dir: sp.Directory = sp.Directory(tempfile.mkdtemp())
    progress_data.update({"current": 0, "total": 0, "done": False, "zip_path": None})
    list_files: list[UploadFile] = []
    list_files.extend(pdfs)
    list_files.extend(images)
    progress_data.update({"current": 0, "total": 0, "done": False, "zip_path": None})
    total_files = len(list_files)
    progress_data['total'] = total_files
    src_df: pd.DataFrame
    
    # Salvar todos os arquivos recebidos
    try:
        sheet_bytes: bytes = await file_sheet.read()
        src_df: pd.DataFrame = ReadFileSheet(io.BytesIO(sheet_bytes), lib_sheet=LibSheet.EXCEL).get_dataframe()
        for current_file in list_files:
            if current_file is None:
                continue
            
            file_name = current_file.filename
            if file_name is None:
                continue
            
            content: bytes = await current_file.read()
            file_path: str = temp_dir.join_file(file_name).absolute()
            with open(file_path, "wb") as f:
                f.write(content)
    except Exception as e:
        progress_data.update({"done": True, "zip_path": None})
        print(f"[ERRO] Falha ao processar documentos: {e}")
        return JSONResponse({"error": str(e)}, status_code=500)
    
    # Enviar os arquivos para processamento
    """
    task_id: str: id do processo.
    df: pd.Dataframe: aponta para um dataframe com dados base para o filtro de dados
    col_find: str: coluna onde o texto deve ser filtrado
    col_new_name: str: coluna que aponta para o novo nome de arquivo.
    files: list[File]: aponta para uma lista de arquivos.
    output_dir: Directory: diretório destino dos arquivos.
    """
    input_files = sp.InputFiles(temp_dir)
    files_path = input_files.pdfs
    files_path.extend(input_files.images)
    
    send_args: dict[str, object] = {
        'task_id': task_id,
        'df': src_df,
        'col_find': column_name,
        'col_new_name': column_name,
        'files': files_path,
        'output_dir': temp_dir,
    }
    thread = threading.Thread(target=thread_organize_documents_with_sheet, kwargs=send_args)
    thread.start()
    return {"message": "Processamento iniciado", "task_id": task_id}
    
    """
    except Exception as e:
        progress_data.update({"done": True, "zip_path": None})
        print(f"[ERRO] Falha ao tentar renomear aquivos: {e}")
        return JSONResponse({"error": str(e)}, status_code=500)
    else:
        # Retornar o ZIP finalizado
        return StreamingResponse(
            zip_buffer,
            media_type="application/zip",
            headers={"Content-Disposition": "attachment; filename=filtrado_com_tabela.zip"},
        )
    """


@app.post(f"/{route_info['rt_process_pattern']}")
async def organize_documents_with_pattern(
            pdfs: list[UploadFile] = File(default=[]),
            images: list[UploadFile] = File(default=[]),
            pattern: str = Form(default=None), 
            digitalized_type: str = Form(default=None),
        ):
    """
    Rota alternativa usada quando o usuário digita um padrão de texto
    ao invés de enviar planilha XLSX e nome de coluna.
    Retorna um ZIP com os arquivos processados.
    
    :param document_type: CARTA/EPI/GERNÉRICO
    """
    if not pattern:
        if not digitalized_type:
            e = "O parâmetro 'pattern' é obrigatório para documentos genéricos."
            print()
            return JSONResponse({"error": str(e)}, status_code=500)

    task_id = str(uuid.uuid4())
    progress_data = create_progress_with_id(task_id)
    progress_data.update({"current": 0, "total": 0, "done": False, "zip_path": None})
    total_files = len(images) + len(pdfs)
    progress_data['total'] = total_files
    
    pdfs.extend(images)
    images.clear()
    input_files_document: ListItems[DictOriginInfo] = ListItems()
    try:
        for document in pdfs:
            if document is None:
                continue

            file_name = document.filename
            if file_name is None:
                continue
            current = DictOriginInfo()
            extension_file = f".{file_name.split('.')[-1]}"
            current.set_name(file_name.replace(extension_file, ''))
            current.set_filename_with_extension(file_name)
            current.set_extension(extension_file)
            current.set_file_bytes(await document.read())
            input_files_document.append(current)
    except Exception as e:
        print(e)
        return {"message": "Falha ao tentar ler os arquivos", "task_id": task_id}
        
    send_args: dict[str, object] = {
        'task_id': task_id,
        'pdfs': input_files_document,
        'images': ListItems(),
        'pattern': pattern,
        'digitalized_type': digitalized_type,
    }
    thread = threading.Thread(target=thread_organize_documents, kwargs=send_args)
    thread.start()
    return {"message": "Processamento iniciado", "task_id": task_id}



