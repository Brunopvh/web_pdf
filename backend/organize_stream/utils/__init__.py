from sheet_stream import clean_string, BAD_STRING_CHARS
from sheet_stream.type_utils import (
    HeadCell, HeadValues, ColumnsTable, ListColumnBody, ListString, ArrayString,
    TableDocuments, TableRow
)

import soup_files as sp
import convert_stream as cs
import ocr_stream as ocr
import sheet_stream as sheet

_remove_end_name: list[str] = ['-']
_remove_start_name: list[str] = ['-']


def remove_bad_chars(text: str) -> str:
    return clean_string(text)


def fmt_str_file(
            filename: str, *,
            max_char: int = 80,
            upper_case: bool = True
        ) -> str:
    filename = remove_bad_chars(filename)

    for c in _remove_end_name:
        if filename[-1] == c:
            filename = filename[:-1]
    for c in _remove_start_name:
        while c in filename[0]:
            filename = filename[1:]
    while '--' in filename:
        filename = filename.replace('--', '-')
    if upper_case:
        filename = filename.upper()
    if len(filename) <= max_char:
        return filename
    return filename[0:max_char]
