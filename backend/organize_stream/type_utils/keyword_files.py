from __future__ import annotations
from enum import StrEnum
from typing import TypeAlias, Union
from io import BytesIO
from organize_stream.utils import sp  #sheet, ListString, ListColumnBody
from organize_stream.erros import *
from sheet_stream.type_utils import (
    get_hash_from_bytes, ColumnsTable, ListString, ListColumnBody
)
import shutil

DiskFile: TypeAlias = Union[str, sp.File, bytes, BytesIO]


class EnumDigitalDoc(StrEnum):

    GENERIC = 'generic'
    CARTA_CALCULO = 'carta_calculo'
    EPI = 'epi'


class ColumnsKeyFiles(StrEnum):

    SRC_ORIGIN_FILE = 'SRC_FILE_PATH'
    SRC_ORIGIN_NAME = 'FILE_NAME'
    SRC_DIRECTORY = 'DIRECTORY'
    FILE_TYPE = 'FILE_TYPE'
    NEW_DEST_FILE = 'NEW_FILE_NAME'
    UNIQUE_KEY = 'UNIQUE_KEY'


class DictFileInfo(dict):
    """
    Guardar informações sobre um arquivo
    Nome, diretório de origem, extensão do arquivo entre outras informações.
    """

    def __init__(self):
        super().__init__({})
        self[ColumnsTable.FILE_NAME.value] = None  # Nome do arquivo com a extensão
        self[ColumnsTable.FILETYPE.value] = None  # Extensão do arquivo .txt, png, .pdf ...
        self[ColumnsTable.FILE_PATH.value] = None  # Caminho absoluto do arquivo no disco
        self[ColumnsTable.DIR.value] = None  # Diretório de origem do arquivo.
        self['BYTES'] = None  # Os bytes do arquivo
        self['FILENAME'] = None

    def __hash__(self):
        if self.get_abspath() is not None:
            return hash(self.get_abspath())
        return hash(self.get_file_bytes())

    def get_file_bytes(self) -> bytes | None:
        return self['BYTES']

    def set_file_bytes(self, bt: bytes | None) -> None:
        self['BYTES'] = bt

    def get_directory(self) -> sp.Directory | None:
        return self[ColumnsTable.DIR.value]

    def set_directory(self, d: sp.Directory) -> None:
        self[ColumnsTable.DIR.value] = d

    def get_abspath(self) -> sp.File | None:
        return self[ColumnsTable.FILE_PATH.value]

    def set_abspath(self, file_path: sp.File | None) -> None:
        self[ColumnsTable.FILE_PATH.value] = file_path

    def get_type_document(self) -> sp.LibraryDocs:
        if self.get_extension() in sp.LibraryDocs.IMAGE:
            return sp.LibraryDocs.IMAGE
        elif self.get_extension() in sp.LibraryDocs.PDF:
            return sp.LibraryDocs.PDF
        elif self.get_extension() in sp.LibraryDocs.EXCEL:
            return sp.LibraryDocs.EXCEL
        elif self.get_extension() in sp.LibraryDocs.ODS:
            return sp.LibraryDocs.ODS
        elif self.get_extension() in sp.LibraryDocs.CSV:
            return sp.LibraryDocs.CSV
        return sp.LibraryDocs.ALL

    def get_extension(self) -> str:
        return self[ColumnsTable.FILETYPE.value]

    def set_extension(self, extension: str | None) -> None:
        self[ColumnsTable.FILETYPE.value] = extension

    def get_filename_with_extension(self) -> str | None:
        return self[ColumnsTable.FILE_NAME.value]

    def set_filename_with_extension(self, filename: str | None) -> None:
        self[ColumnsTable.FILE_NAME.value] = filename

    def get_name(self) -> str | None:
        """Retorna o nome do arquivo sem a extensão"""
        return self['FILENAME']

    def set_name(self, name: str | None):
        self['FILENAME'] = name

    def size(self) -> int:
        return len(self)

    def size_keys(self) -> int:
        return len(self.keys())

    def set_value(self, key: str, value: object) -> None:
        self[key] = value

    def clear(self):
        super().clear()
        self[ColumnsTable.FILETYPE.value] = None
        self[ColumnsTable.FILE_PATH.value] = None
        self[ColumnsTable.FILE_NAME.value] = None
        self[ColumnsTable.DIR.value] = None
        self['BYTES'] = None

    def keys(self) -> ListString:
        return ListString(list(super().keys()))

    def id(self) -> str | None:
        if self.get_abspath() is not None:
            return self.get_abspath().basename()
        if self.get_extension() is not None:
            raise ExtensionFileEmptyError(f'Adicione uma extensão de arquivo em {self.get_filename_with_extension()}')
        if self.get_file_bytes() is not None:
            raise ExtensionFileEmptyError(f'{__class__.__name__} os bytes do arquivo não foram adicionados')
        return f'{get_hash_from_bytes(self.get_file_bytes())}{self.get_extension()}'


class DictOriginInfo(DictFileInfo):

    def __init__(self):
        super().__init__()


class DictOutputInfo(DictFileInfo):

    def __init__(self):
        super().__init__()


class DynamicFile(object):

    def __init__(self, file: DiskFile):
        self.disk_file_info = DictFileInfo()

        if isinstance(file, sp.File):
            self.disk_file_info['SRC_INPUT'] = 'FILE'
            self.disk_file_info.set_abspath(file)
            self.disk_file_info.set_extension(file.extension())
            self.disk_file_info.set_file_bytes(file.path.read_bytes())
            self.disk_file_info.set_filename_with_extension(file.basename())
        elif isinstance(file, bytes):
            self.disk_file_info['SRC_INPUT'] = 'BYTES'
            self.disk_file_info.set_file_bytes(file)
        elif isinstance(file, BytesIO):
            self.disk_file_info['SRC_INPUT'] = 'BYTES_IO'
            self.disk_file_info.set_file_bytes(file.getvalue())
        elif isinstance(file, str):
            file = sp.File(file)
            self.disk_file_info.set_abspath(file)
            self.disk_file_info['SRC_INPUT'] = 'FILE'
            self.disk_file_info.set_extension(file.extension())
            self.disk_file_info.set_file_bytes(file.path.read_bytes())
            self.disk_file_info.set_filename_with_extension(file.basename())
        else:
            raise InvalidSrcFile(
                f'{__class__.__name__} Arquivo inválido ... {file}, use ... bytes|BytesIO|File|str'
            )

    @property
    def id_file(self) -> str | None:
        if (self.get_src_input() == 'BYTES') or (self.get_src_input() == 'BYTES_IO'):
            _id_file = get_hash_from_bytes(self.disk_file_info.get_file_bytes())
        elif (self.get_src_input() == 'STR') or (self.get_src_input() == 'FILE'):
            _id_file = self.disk_file_info.get_abspath().name()
        else:
            _id_file = None
        return _id_file

    @property
    def is_bytes(self) -> bool:
        return self.get_src_input() == 'BYTES'

    @property
    def is_bytes_io(self) -> bool:
        return self.get_src_input() == 'BYTES_IO'

    @property
    def is_file(self) -> bool:
        return self.get_src_input() == 'STR'

    @property
    def is_file_path(self) -> bool:
        return self.get_src_input() == 'FILE'

    def __hash__(self):
        return hash(self.get_file_disk())

    def get_src_input(self) -> str:
        return self.disk_file_info['SRC_INPUT']

    def get_type_document(self) -> sp.LibraryDocs:
        return self.disk_file_info.get_type_document()

    def get_extension(self) -> str | None:
        return self.disk_file_info.get_extension()

    def set_extension(self, extension: str) -> None:
        self.disk_file_info.set_extension(extension)

    def get_file_name(self) -> str | None:
        """Retorna o nome do arquivo com a extensão"""
        if self.disk_file_info.get_filename_with_extension() is not None:
            return self.disk_file_info.get_filename_with_extension()
        extension = self.disk_file_info.get_extension()
        if extension is None:
            raise ExtensionFileEmptyError('Adicione uma extensão de arquivo .png|.pdf|.jpg ...')
        return f'{self.id_file}{extension}'

    def get_file_disk(self) -> DiskFile:
        if self.disk_file_info.get_abspath() is not None:
            return self.disk_file_info.get_abspath()
        return self.disk_file_info.get_file_bytes()

    def set_file_disk(self, file: DiskFile):
        if isinstance(file, sp.File):
            self.disk_file_info['SRC_INPUT'] = 'FILE'
            self.disk_file_info.set_abspath(file)
            self.disk_file_info.set_extension(file.extension())
            self.disk_file_info.set_file_bytes(file.path.read_bytes())
            self.disk_file_info.set_filename_with_extension(file.basename())
        elif isinstance(file, bytes):
            self.disk_file_info['SRC_INPUT'] = 'BYTES'
            self.disk_file_info.set_file_bytes(file)
        elif isinstance(file, BytesIO):
            self.disk_file_info['SRC_INPUT'] = 'BYTES_IO'
            self.disk_file_info.set_file_bytes(file.getvalue())
        elif isinstance(file, str):
            file = sp.File(file)
            self.disk_file_info.set_abspath(file)
            self.disk_file_info['SRC_INPUT'] = 'FILE'
            self.disk_file_info.set_extension(file.extension())
            self.disk_file_info.set_file_bytes(file.path.read_bytes())
            self.disk_file_info.set_filename_with_extension(file.basename())

    def get_bytes(self) -> bytes | None:
        return self.disk_file_info.get_file_bytes()


class OriginFileName(sp.File):

    def __init__(self, filename: str):
        super().__init__(filename)


class DestFilePath(sp.File):

    def __init__(self, filename: str):
        super().__init__(filename)


class DictKeyWordFiles(dict):
    """

    """

    def __init__(self):
        super().__init__({})
        self[ColumnsKeyFiles.SRC_ORIGIN_FILE.value]: DictOriginInfo = DictOriginInfo()
        self[ColumnsKeyFiles.NEW_DEST_FILE.value]: DictOutputInfo = DictOutputInfo()

    def get_origin_file(self) -> DictOriginInfo:
        return self[ColumnsKeyFiles.SRC_ORIGIN_FILE.value]

    def set_origin_file(self, value: DictFileInfo) -> None:
        self[ColumnsKeyFiles.SRC_ORIGIN_FILE.value] = value

    def get_output_file(self) -> DictOutputInfo:
        return self[ColumnsKeyFiles.NEW_DEST_FILE.value]

    def set_output_file(self, value: DictFileInfo) -> None:
        self[ColumnsKeyFiles.NEW_DEST_FILE.value] = value

    def set_output_dir(self, d: sp.Directory) -> None:
        if not isinstance(d, sp.Directory):
            return
        if self[ColumnsKeyFiles.NEW_DEST_FILE.value] is not None:
            self[ColumnsKeyFiles.NEW_DEST_FILE.value].set_directory(d)
            if self.get_output_file() is not None:
                if self.get_output_file().get_filename_with_extension() is not None:
                    self[ColumnsKeyFiles.NEW_DEST_FILE.value].set_abspath(
                        d.join_file(self.get_output_file().get_filename_with_extension())
                    )

    def __repr__(self):
        return f'KeyWordsFileNames: {super().__repr__()}'

    def __hash__(self):
        return self.get_origin_file().__hash__()

    def __eq__(self, other):
        if self.get_origin_file() is not None and other.get_origin_file() is not None:
            return self.get_origin_file() == other.get_origin_file()
        return self.__hash__() == other.__hash__()

    def keys(self) -> ListString:
        return ListString(list(super().keys()))

    def save_bytes(self, output_dir: sp.Directory) -> tuple[DictOriginInfo, DictOutputInfo | None, bool]:
        """
            Salva os bytes do arquivo original no novo caminho absoluto gerado.
        """
        if self.get_output_file().get_filename_with_extension() is None:
            raise DiskFileInvalidError()
        if self.get_output_file().get_file_bytes() is None:
            if self.get_origin_file().get_file_bytes() is None:
                raise DiskFileInvalidError()
            out: DictOutputInfo = self.get_output_file()
            out.set_file_bytes(self.get_origin_file().get_file_bytes())
            self.set_output_file(out)

        try:
            output_dir.mkdir()
            output_file: sp.File = output_dir.join_file(self.get_output_file().get_filename_with_extension())

            with open(output_file.absolute(), 'wb') as f:
                f.write(self.get_output_file().get_file_bytes())
        except Exception as e:
            print(f'{__class__.__name__} Error: {e}')
            return self.get_origin_file(), None, False
        else:
            return self.get_origin_file(), self.get_output_file(), False

    def move(self, output_dir: sp.Directory) -> tuple[DictFileInfo, DictFileInfo | None, bool]:
        if self.get_origin_file() is None:
            raise DiskFileInvalidError()
        if self.get_output_file() is None:
            raise DiskFileInvalidError()
        if self.get_output_file().get_abspath() is None:
            raise DiskFileInvalidError()
        if self.get_output_file().get_name() is None:
            raise DiskFileInvalidError()

        _count = 0
        _file_name = self.get_output_file().get_name()
        _ext = self.get_output_file().get_extension()
        output_file: sp.File = output_dir.join_file(self.get_output_file().get_filename_with_extension())
        if output_file.exists():
            while True:
                _count += 1
                output_file = output_dir.join_file(f'{_file_name}-{_count}{_ext}')
                if not output_file.exists():
                    break
            
        try:
            shutil.move(self.get_origin_file().get_abspath().absolute(), output_file.absolute())
        except Exception as e:
            print(f'{__class__.__name__} Error: {e}')
            return self.get_origin_file(), None, False
        else:
            return self.get_origin_file(), self.get_output_file(), True
