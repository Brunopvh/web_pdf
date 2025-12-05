#!/usr/bin/env python3
"""

"""
from __future__ import annotations
from fastapi import UploadFile, File
from fastapi import APIRouter
import uuid
import tempfile
import threading
from organize_stream.library.common import (
    create_progress_with_id, BuildAssets, AssetsFrontEnd,
)
from organize_stream.library.app_threads import thread_images_to_pdfs

# JSON ASSETS
_dir_asset = BuildAssets.asset_dir
_assets: AssetsFrontEnd = BuildAssets().set_dir_assets(_dir_asset).build()
jsonAssets: dict = _assets.get_dict_assets()
router_img_to_pdf = APIRouter()


# =============== CONVERTER IMAGENS EM PDF ===============
@router_img_to_pdf.post(f"/{jsonAssets['rt_imgs_to_pdf']}")
async def images_to_pdfs(files: list[UploadFile] = File(...)):
    # Gera um ID único para esta tarefa
    task_id = str(uuid.uuid4())
    # Inicializa o estado de progresso para este ID
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

