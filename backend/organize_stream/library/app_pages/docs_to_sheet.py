from __future__ import annotations
from fastapi import APIRouter
from typing import Any
from fastapi import UploadFile, File
from fastapi.responses import JSONResponse
import uuid
import threading

from sheet_stream import ListItems, ListString
from organize_stream.library.common.assets import (
    get_json_info, FILE_PATH_ASSETS, AssetsFrontEnd, BuildAssets
)
from organize_stream.library.progress_route import (
    create_progress_with_id, get_id_progress_state, thread_docs_to_sheet,
)
from organize_stream.type_utils import DictOriginInfo

# JSON ASSETS
_dir_asset = BuildAssets.asset_dir
_assets: AssetsFrontEnd = BuildAssets().set_dir_assets(_dir_asset).build()
jsonAssets: dict[str, Any] = _assets.get_dict_assets()

# Define o roteador para as rotas de progresso
router_docs_to_sheet = APIRouter()


# =============== CONVERTER DOCUMENTOS EM PLANILHA ===============
@router_docs_to_sheet.post(f"/{jsonAssets['rt_docs_to_sheet']}")
async def docs_to_sheet(files: list[UploadFile] = File(...)):
    # Gera um ID único para esta tarefa
    task_id = str(uuid.uuid4())
    # Inicializa o estado de progresso para este ID
    create_progress_with_id(task_id)
    current_progress: dict[str, Any] = get_id_progress_state(task_id)
    input_files_document: ListItems[DictOriginInfo] = ListItems()
    
    for document in files:
        if document is None:
            continue

        file_name = document.filename
        if file_name is None:
            continue
        
        try:
            current = DictOriginInfo()
            extension_file = f".{file_name.split('.')[-1]}"
            current.set_name(file_name.replace(extension_file, ''))
            current.set_filename_with_extension(file_name)
            current.set_extension(extension_file)
            current.set_file_bytes(await document.read())
            input_files_document.append(current)
        except Exception as err:
            current_progress.update({"done": True, "zip_path": None})
            error_message = f"Falha ao ler ou classificar os arquivos: {err}"
            print(f"\n[ERRO] {error_message}")
            return JSONResponse({"error": error_message}, status_code=500)

    values_documents: dict[str, Any] = {
        'task_id': task_id,
        'documents': input_files_document,
    }
    thread = threading.Thread(target=thread_docs_to_sheet, kwargs=values_documents)
    thread.start()
    return {"message": "Conversão de documentos em planilha iniciada", "task_id": task_id}
