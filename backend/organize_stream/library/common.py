import tempfile
import soup_files as sp
from typing import Any


def get_temp_dir():
    # Criar diretório temporário para saída
    temp_dir = tempfile.mkdtemp()
    return temp_dir


# ===================== OBTER ROTAS E IPS DO ARQUIVO JSON ====
def get_json_info(file_json: sp.File) -> dict[str, Any] | None:
    """
        Ler o arquivo .json para obter informações de rotas e IPS.
    """
    try:
        data: sp.JsonData = sp.JsonConvert.from_file(file_json).to_json_data()
        return data.to_dict()
    except Exception as err:
        print(err)
    return None



