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
    # 1. Gera um ID único para esta tarefa
    task_id = str(uuid.uuid4())
    # 2. Inicializa o estado de progresso para este ID
    create_progress_with_id(task_id)
    current_progress: dict[str, Any] = get_id_progress_state(task_id)

    extension_images = ListString(['.png', '.jpg', '.jpeg'])
    extension_pdfs = ListString(['.pdf'])
    bytes_image: ListItems[bytes] = ListItems()
    bytes_pdfs: ListItems[bytes] = ListItems()

    # Salvar os uploads em arquivos temporários
    for current_file in files:
        content: bytes = await current_file.read()
        try:
            extension = '.' + current_file.filename.split('.')[-1]
            if extension_images.contains(extension, case=True, iqual=True):
                bytes_image.append(content)
            elif extension_pdfs.contains(extension, case=True, iqual=True):
                bytes_pdfs.append(content)
        except Exception as err:
            current_progress.update({"done": True, "zip_path": None})
            error_message = f"Falha ao ler ou classificar os arquivos: {err}"
            print(f"\n[ERRO] {error_message}")
            return JSONResponse({"error": error_message}, status_code=500)

    values_documents: dict[str, Any] = {
        'task_id': task_id,
        'images': bytes_image,
        'pdfs': bytes_pdfs,
    }
    thread = threading.Thread(target=thread_docs_to_sheet, kwargs=values_documents)
    thread.start()
    return {"message": "Conversão de documentos em planilha iniciada", "task_id": task_id}
