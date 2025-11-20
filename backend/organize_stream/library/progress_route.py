from fastapi import APIRouter
from fastapi.responses import JSONResponse
from typing import Any
from io import BytesIO
import tempfile
import convert_stream as cs
import zipfile
import os
import soup_files as sp
from organize_stream.document import CreateNewFile
from organize_stream.type_utils import (
    FilterData, FilterText, LibDigitalized, DiskOriginInfo, DiskOutputInfo
)
from sheet_stream import ListItems

# Define o roteador para as rotas de progresso
router = APIRouter()
TASK_PROGRESS_STATE: dict[str, dict[str, Any]] = {}


def create_progress_with_id(task_id: str) -> dict[str, Any]:
    """
        Cria um progresso vazio e adiciona no dicionário global.
    """
    new_state = {
        "current": 0,
        "total": 0,
        "done": False,
        "zip_path": None,
        "task_id": task_id,
        "message": "Aguarde!",
    }
    TASK_PROGRESS_STATE[task_id] = new_state
    return new_state


def get_id_progress_state(task_id: str) -> dict[str, Any] | None:
    """Obtém o estado de progresso para um ID de tarefa específico."""
    return TASK_PROGRESS_STATE.get(task_id)


# =============== ROTA PROGRESSO ==================
@router.get("/progress/{task_id}")
async def get_json_progress(task_id: str) -> JSONResponse:
    """
        Retorna o status do processamento para o frontend.
    """
    # Obtém o estado usando o ID da tarefa na URL
    current_progress = get_id_progress_state(task_id)
    if current_progress is None:
        return JSONResponse({
        "current": 0,
        "total": 0,
        "progress": 0,
        "done": False,
        "task_id": task_id,
    })
        
    if current_progress["total"]:
        pbar = ((current_progress["current"] + 1) / current_progress["total"]) * 100
    else:
        pbar = 0
    return JSONResponse({
        "current": current_progress["current"],
        "total": current_progress["total"],
        "progress": pbar,
        "done": current_progress["done"],
        "task_id": task_id,
    })


def thread_images_to_pdfs(images: list[str], task_id: str) -> None:
    """
    Recebe uma lista de imagens e junta tudo em arquivos pdf, o download final
    são arquivos .pdf dentro de um .zip
    """
    # Criar diretório temporário para saída
    temp_dir = tempfile.mkdtemp()
    _output_zip = os.path.join(temp_dir, "resultado.zip")
    pdf_stream = cs.PdfStream()
    current_progress: dict[str, Any] = get_id_progress_state(task_id)

    try:
        current_progress['total'] = len(images)
        with zipfile.ZipFile(_output_zip, "w") as zipf:
            for idx, path in enumerate(images):
                current_progress["current"] = idx
                with open(path, "rb") as fp:
                    raw_bytes = fp.read()
                im = cs.ImageObject.create_from_bytes(raw_bytes)
                pdf_stream.add_image(im)
                doc = pdf_stream.to_document()
                pdf_bytes: BytesIO = doc.to_bytes()
                filename = f"documento_{idx}.pdf"
                zipf.writestr(filename, pdf_bytes.getvalue())
                pdf_stream.clear()
                del doc
        # finalizou
        current_progress.update({"done": True, "zip_path": _output_zip})
    except Exception as e:
        current_progress.update({"done": True, "zip_path": None})
        print(f"[ERRO] Worker falhou: {e}")
        
    
def thread_organize_documents(**kwargs: dict[str, Any]) -> None:
    """
    Recebe uma lista de imagens e junta tudo em arquivos pdf, o download final
    são arquivos .pdf dentro de um .zip
    """
    # Criar diretório temporário para saída
    temp_dir: sp.Directory = sp.Directory(tempfile.mkdtemp())
    temp_dir.mkdir()
    _output_zip: str = temp_dir.join_file("resultado.zip").absolute()
    current_progress: dict[str, Any] = get_id_progress_state(kwargs['task_id'])
    current_progress['total'] = len(kwargs['images']) + len(kwargs['pdfs'])
    current_progress['current'] = 0
    
    name_finder: CreateNewFile
    if kwargs['document_type'] == 'EPIS':
        name_finder = CreateNewFile(lib_digitalized=LibDigitalized.EPI)
    elif kwargs['document_type'] == 'CARTAS':
        name_finder = CreateNewFile(lib_digitalized=LibDigitalized.CARTA_CALCULO)
    else:
        if kwargs['pattern'] is None:
            current_progress.update({"done": True, "zip_path": None})
            print(f"DEBUG: thread_organize_documents falhou, o filtro de texto é nulo!")
            return
        filter_text = FilterText(kwargs['pattern'])
        name_finder = CreateNewFile(filters=filter_text)
           
    final_bytes: BytesIO | None
    try:
        count = 0
        files_image: ListItems[DiskOriginInfo] = kwargs['images']
        files_pdf: ListItems[DiskOriginInfo] = kwargs['pdfs']
        total = len(files_image) + len(files_pdf)
        
        for num, file_info in enumerate(files_image):
            current_progress["current"] = count
            count += 1
            print(f'{num+1}/{total}')
            name_finder.add_disk_file(file_info) 
        for num, file_info in enumerate(files_pdf):
            current_progress["current"] = count
            count += 1
            print(f'{num+1}/{total}')
            name_finder.add_disk_file(file_info) 
            
        final_bytes: BytesIO | None = name_finder.export_keys_to_zip()
        if final_bytes is None:
            current_progress.update({"done": True, "zip_path": None})
            print(f"DEBUG: thread_organize_documents falhou, o arquivo zip é nulo!")
            return
    except Exception as e:
        current_progress.update({"done": True, "zip_path": None})
        print(f"\n[ERRO] thread_organize_documents falhou ao tentar gerar o arquivo ZIP: {e}")
    else:
        try:
            path_excel = temp_dir.join_file('dados.xlsx')
            name_finder.export_log_actions().to_excel(path_excel.absolute(), index=False)
            final_bytes.seek(0)
            with zipfile.ZipFile(final_bytes, 'a', zipfile.ZIP_DEFLATED) as zipf:
                # writestr adiciona bytes na memória.
                zipf.writestr('dados.xlsx', path_excel.path.read_bytes())
            final_bytes.seek(0)
            with open(_output_zip, 'wb') as fp:
                fp.write(final_bytes.getvalue())
            
        except Exception as e:
            current_progress.update({"done": True, "zip_path": None})
            print(f"\n[ERRO] thread_organize_documents falhou ao tentar salvar o arquivo ZIP: {e}")
        else:
            current_progress.update({"done": True, "zip_path": _output_zip})
        