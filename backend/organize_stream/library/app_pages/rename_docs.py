#!/usr/bin/env python3
"""

"""
from __future__ import annotations
from fastapi import UploadFile, File, APIRouter
from fastapi.responses import JSONResponse
from fastapi import Form
import uuid

import io
import soup_files as sp
import pandas as pd
import tempfile
import threading
from organize_stream.library.common import (
    create_progress_with_id, BuildAssets, AssetsFrontEnd,
)
from organize_stream import DictOriginInfo
from organize_stream.library.app_threads import (
    thread_organize_documents_with_sheet, thread_organize_documents
)
from sheet_stream import (
    ListItems, ReadFileSheet, LibSheet
)


# JSON ASSETS
_dir_asset = BuildAssets.asset_dir
_assets: AssetsFrontEnd = BuildAssets().set_dir_assets(_dir_asset).build()
jsonAssets: dict = _assets.get_dict_assets()
router_rename = APIRouter()

# ===================== ROTA UNIFICADA PROCESSAR DOCUMENTOS =====================


@router_rename.post(f"/{jsonAssets['rt_process_docs']}")
async def organize_documents_with_sheet(
        pdfs: list[UploadFile] = File(default=[]),
        images: list[UploadFile] = File(default=[]),
        file_sheet: UploadFile = File(default=None),
        column_name: str = Form(default=None),
):
    """
        Rota para processar PDFs, imagens e renomear com base em planilha Excel.
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

    # Enviar os arquivos para processamento em thread separada
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


@router_rename.post(f"/{jsonAssets['rt_process_pattern']}")
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

