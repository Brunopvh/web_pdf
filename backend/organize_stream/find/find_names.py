#!/usr/bin/env python3
from __future__ import annotations
from abc import ABC, abstractmethod
import pandas as pd
from organize_stream.type_utils import (
    DigitalizedDocument, OriginFileName, DestFilePath,
    FilterData,

)

from organize_stream.utils import (
    ArrayString, ListString, ListColumnBody, ColumnsTable,
    sp, fmt_str_file, HeadValues, HeadCell, sheet
)


def get_column_values(df: pd.DataFrame, col: str) -> ArrayString:
    try:
        _values = df[col].astype('str').values.tolist()
    except Exception as e:
        print(e)
        return ArrayString([])
    else:
        return ArrayString(_values)


class SearchableText(object):
    default_elements: sheet.TableDocuments = sheet.TableDocuments.create_void_dict()
    default_columns: HeadValues = HeadValues([HeadCell(x) for x in list(default_elements.keys())])

    def __init__(self):
        self.elements: sheet.TableDocuments = sheet.TableDocuments.create_void_dict()

    def __repr__(self):
        return f'SearchableText\nHead: {self.head}\nBody: {self.body}'

    def is_empty(self) -> bool:
        return len(self.elements[HeadCell(ColumnsTable.TEXT)]) == 0

    @property
    def head(self) -> HeadValues:
        return HeadValues([HeadCell(x) for x in list(self.elements.keys())])

    @property
    def body(self) -> list[ListColumnBody]:
        return [ListColumnBody(HeadCell(_k), self.elements[_k]) for _k in self.elements.keys()]

    @property
    def first(self) -> dict[str, str]:
        if self.is_empty():
            return {}
        cols: HeadValues = self.head
        _first = {}
        for col in cols:
            _first[col] = self.elements[col][0]
        return _first

    @property
    def last(self) -> dict[str, str]:
        if self.is_empty():
            return {}
        cols = self.head
        _last = {}
        for col in cols:
            _last[col] = self.elements[col][-1]
        return _last

    @property
    def length(self) -> int:
        return len(self.elements[HeadCell(ColumnsTable.TEXT)])

    @property
    def files(self) -> ListColumnBody:
        return self.elements[HeadCell(ColumnsTable.FILE_PATH)]

    def get_item(self, idx: int) -> dict[str, str]:
        cols: HeadValues = self.head
        try:
            _item = {}
            for col in cols:
                _item[col] = self.elements[col][idx]
            return _item
        except Exception as err:
            print(err)
            return {}

    def get_column(self, name: str) -> ListColumnBody:
        return self.elements[HeadCell(name)]

    def add_line(self, line: dict[str, str]) -> None:
        cols_in_line: HeadValues = HeadValues([HeadCell(x) for x in list(line.keys())])
        cols_in_searchable: HeadValues = self.head
        for col in cols_in_searchable:
            if cols_in_line.contains(col, case=True, iqual=True):
                self.elements[col].append(line[col])

    def clear(self) -> None:
        for _k in self.elements.keys():
            self.elements[_k].clear()

    def to_string(self) -> str:
        """
            Retorna o texto da coluna TEXT em formato de string
        ou 'nas' em caso de erro nas = Not a String
        """
        try:
            return ' '.join(self.elements[HeadCell(ColumnsTable.TEXT)])
        except Exception as e:
            print(e)
            return 'nan'

    def to_data_frame(self) -> pd.DataFrame:
        return pd.DataFrame.from_dict(self.elements)

    def to_file_json(self, file: sp.File):
        """Exporta os dados da busca para arquivo .JSON"""
        dt = sp.JsonConvert.from_dict(self.elements).to_json_data()
        dt.to_file(file)

    def to_file_excel(self, file: sp.File):
        """Exporta os dados da busca para arquivo .XLSX"""
        self.to_data_frame().to_excel(file.absolute(), index=False)

    @classmethod
    def create(cls, df: pd.DataFrame) -> SearchableText:
        cols: list[str] = df.columns.tolist()
        _values: list[ListColumnBody] = []
        for col in cols:
            _values.append(
                ListColumnBody(
                    col, ListString(df[col].astype('str').values.tolist())
                )
            )
        s = cls()
        s.elements = sheet.TableDocuments(_values)
        return s


class NameFinder(ABC):

    def __init__(self, output_dir: sp.Directory):
        self.output_dir = output_dir

    @abstractmethod
    def get_new_name(self, digitalized: DigitalizedDocument) -> dict[OriginFileName, DestFilePath]:
        pass


class NameFinderInnerText(NameFinder):

    def __init__(self, output_dir: sp.Directory):
        super().__init__(output_dir)

    def get_new_name(self, digitalized: DigitalizedDocument) -> dict[OriginFileName, DestFilePath]:
        src_file = digitalized.file_path_origin
        filename = digitalized.get_output_name_with_extension()
        if (src_file is None) or (filename is None):
            return {}
        if filename == '':
            return {}
        output_path = self.output_dir.join_file(filename)
        return {OriginFileName(src_file.absolute()): DestFilePath(output_path.absolute())}


class NameFinderInnerData(NameFinder):

    def __init__(self, output_dir: sp.Directory, *, filters: FilterData):
        super().__init__(output_dir)
        self.filter_data = filters

    def get_values(self, df: pd.DataFrame, col: str) -> ArrayString:
        return get_column_values(df, col)

    def get_include_names(self, idx: int) -> str | None:
        if len(self.filter_data.cols_in_name) == 0:
            return None

        values = ArrayString([])
        for col in self.filter_data.cols_in_name:
            try:
                current_text = self.filter_data.src_df[col].astype('str').values.tolist()[idx]
            except Exception as e:
                pass
            else:
                if (current_text == 'nan') or (current_text == 'NaN') \
                        or (current_text == 'NaD') or (current_text == 'NaT') \
                        or (current_text == '') or (current_text is None) or (current_text == 'None'):
                    continue
                values.append(current_text)
        if values.length == 0:
            return None
        new_name = ''
        for i in values:
            new_name = f'{new_name}-{i}'
        return new_name

    def get_new_name(self, digitalized: DigitalizedDocument) -> dict[OriginFileName, DestFilePath]:
        extension_file = digitalized.extension_file
        _origin_path = digitalized.file_path_origin
        if (extension_file is None) or (_origin_path is None):
            return {}

        # Lista de valores da coluna texto.
        list_values_find: ArrayString = self.get_values(self.filter_data.src_df, self.filter_data.col_find)

        # Lista de valores da coluna com novos nomes de arquivo.
        content_new_names: ArrayString = self.get_values(self.filter_data.src_df, self.filter_data.col_new_name)

        # Lista de valores com as linhas de texto do arquivo em formato list[str].
        lines_in_doc: ArrayString = ArrayString(digitalized.get_lines_keys())

        line_df: str
        idx_df: int
        output_name: str = None
        for idx_df, line_df in enumerate(list_values_find):
            if not lines_in_doc.contains(line_df, case=False, iqual=False):
                continue

            output_name = content_new_names[idx_df]
            if (output_name == 'nan') or (output_name is None):
                output_name = ''
            include_strings = self.get_include_names(idx_df)
            if include_strings is not None:
                output_name = f'{output_name}-{include_strings}'
            if output_name == '':
                continue
            output_name: str = fmt_str_file(output_name)
            break

        if output_name is None:
            return {}

        output_name = f'{output_name}{extension_file}'
        _dest_path = self.output_dir.join_file(output_name)

        if not isinstance(_dest_path, sp.File):
            return {}
        if not isinstance(_origin_path, sp.File):
            return {}
        return {OriginFileName(_origin_path.absolute()): DestFilePath(_dest_path.absolute())}
