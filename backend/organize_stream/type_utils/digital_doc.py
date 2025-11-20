from __future__ import annotations
from abc import ABC, abstractmethod
import pandas as pd
from organize_stream.erros import TableFileEmptyError
from sheet_stream import (
    TableDocuments, ArrayString, ColumnsTable,
    ListColumnBody
)
import soup_files as sp


class FilterText(object):
    """
        Padrão de informações a serem filtradas em um documento.
    """

    def __init__(
                self,
                find_txt: str, *,
                separator: str = ' ',
                case: bool = False,
                iqual: bool = False,
                key_words: list[str] = None,
            ):
        self.find_txt: str = find_txt
        self.case: bool = case
        self.iqual: bool = iqual
        self.separator: str = separator
        self.key_words: list[str] = key_words


class FilterData(object):

    def __init__(
                self,
                src_df: pd.DataFrame, *,
                col_find: str,
                col_new_name: str,
                cols_in_name: list[str],
            ):
        self.col_find: str = col_find
        self.col_new_name: str = col_new_name
        self.cols_in_name: list[str] = cols_in_name
        self.src_df: pd.DataFrame = src_df.astype('str')


class DigitalizedDocument(ABC):

    default_filter: FilterText | None = None

    def __init__(self, tb: TableDocuments, *, filters: FilterText):
        self.tb: TableDocuments = tb
        if self.tb.length == 0:
            raise TableFileEmptyError('A tabela de arquivos não pode estar vazia!')
        self.filters: FilterText = filters

    @property
    def uniq_key_words(self) -> ArrayString:
        return ArrayString(self.filters.key_words)

    @property
    def file_path_origin(self) -> sp.File | None:
        value: ListColumnBody = self.tb.get_column(ColumnsTable.FILE_PATH)
        if value.is_empty:
            return None
        if (value[0] == '') or (value[0] == 'nan') or (value[0] == 'None') \
                or (value[0] == '-') or (value[0] == 'NaT'):
            return None
        try:
            file_path = sp.File(value[0])
        except Exception as e:
            print(e)
            return None
        else:
            if file_path.path.exists():
                return file_path
            return None

    @property
    def dir_path_origin(self) -> sp.Directory | None:
        value: ListColumnBody = self.tb.get_column(ColumnsTable.DIR)
        if value.is_empty:
            return None
        if (value[0] == '') or (value[0] == 'nan') or (value[0] == 'None') \
                or (value[0] == '-') or (value[0] == 'NaT'):
            return None
        try:
            _dir_path = sp.Directory(value[0])
        except Exception as e:
            print(e)
            return None
        else:
            if _dir_path.path.exists():
                return _dir_path
            return None

    @property
    def extension_file(self) -> str | None:
        value: ListColumnBody = self.tb.get_column(ColumnsTable.FILETYPE)
        if value.is_empty:
            return None
        if (value[0] == '') or (value[0] == 'nan') or (value[0] == 'None') \
                or (value[0] == '-') or (value[0] == 'NaT'):
            return None
        return value[0]

    @property
    def lines(self) -> ListColumnBody:
        return self.tb.get_column(ColumnsTable.TEXT)

    def __repr__(self):
        return f'{__class__.__name__}: {self.get_line_key()}'

    @abstractmethod
    def get_line_key(self) -> str:
        pass

    def get_lines_keys(self) -> ArrayString:
        return self.tb.get_column(ColumnsTable.TEXT)

    def get_output_name_with_extension(self) -> str | None:
        """Retorna o novo nome do arquivo, incluindo a extensão"""
        if (self.extension_file is None) or (self.extension_file == '') or (self.extension_file == 'nan'):
            return None
        if (self.get_output_name_str() is None) or (self.get_output_name_str() == '') or (self.get_output_name_str() == 'nan'):
            return None
        return f'{self.get_output_name_str()}{self.extension_file}'

    @abstractmethod
    def get_output_name_str(self) -> str | None:
        """
        Retorna o novo nome do arquivo, sem a extensão
        """
        pass

    def to_excel(self, file: sp.File):
        self.tb.to_data().to_excel(file.absolute())

    def to_file_text(self, file: sp.File):
        lines = self.lines
        print(f'Exportando: {file.absolute()}')
        with open(file.absolute(), 'w', encoding='utf-8') as f:
            f.writelines(lines)
