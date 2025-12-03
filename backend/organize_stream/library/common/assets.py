from __future__ import annotations
import tempfile
import soup_files as sp
from typing import Any
from organize_stream.text_extract.text_extract import OcrImage

FILE_PATH_ASSETS: sp.File = None


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


class AssetsFrontEnd(object):
    # Variável de classe para armazenar a única instância
    _instance = None
    _initialized = False

    def __new__(cls, *args, **kwargs):
        # Verifica se a instância já existe
        if cls._instance is None:
            # Se não existir, cria a instância chamando o __new__ da classe pai (object)
            cls._instance = super(AssetsFrontEnd, cls).__new__(cls)
        # Retorna a única instância (existente ou recém-criada)
        return cls._instance

    def __init__(self, **kwargs) -> None:
        
        if not hasattr(self, '_initialized'):
            print('Asset Iniciado')
            self._initialized = True  # Marca como inicializado
            self.kwargs: dict = kwargs
        self.__dir_assets: sp.Directory = None
        
    def get_dir_assets(self) -> sp.Directory:
        return self.__dir_assets    
        
    def set_dir_assets(self, new: sp.Directory):
        if new is not None:
            self.__dir_assets = new

    def get_file_json_assets(self) -> sp.File:
        if self.get_dir_assets() is None:
            raise ValueError(f'{__class__.__name__} Diretório assets é None')
        return self.get_dir_assets().join_file('ips.json')

    def get_dict_assets(self) -> dict[str, Any]:
        data: sp.JsonData = sp.JsonConvert.from_file(self.get_file_json_assets()).to_json_data()
        return data.to_dict()


class BuildAssets(object):
    
    asset_dir: sp.Directory = None
    
    def __init__(self) -> None:
        self._DIR_ASSETS = None
        
    def set_dir_assets(self, d: sp.Directory) -> BuildAssets:
        if d is not None:
            self._DIR_ASSETS = d
        return self
        
    def build(self) -> AssetsFrontEnd:
        if self._DIR_ASSETS is None:
            raise ValueError('Diretório assets é None!!!')
        
        _asset = AssetsFrontEnd()
        _asset.set_dir_assets(self._DIR_ASSETS)
        return _asset