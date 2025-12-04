from fastapi import APIRouter
from fastapi.responses import JSONResponse
from typing import Any

# Define o roteador para as rotas de progresso
router = APIRouter()
TASK_PROGRESS_STATE: dict[str, dict[str, Any]] = {}


def create_progress_with_id(task_id: str) -> dict[str, Any]:
    """
        Cria um progresso vazio e adiciona no dicionário global.
        
    TASK_PROGRESS_STATE
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
    """
        Obtém o estado de progresso para um ID de tarefa específico.
    """
    try:
        return TASK_PROGRESS_STATE.get(task_id)
    except Exception as e:
        print(e)
        return None


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
