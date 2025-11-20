#!/usr/bin/env python3
from __future__ import annotations
from typing import Callable, Optional
from organize_stream.utils import (
    cs, sp, sheet, ocr, HeadValues, ListColumnBody, HeadCell, ListString,
    ColumnsTable, TableDocuments,
)


class OcrImage(ocr.RecognizeImage):
    """
    Singleton para reconhecimento de texto em imagens
    """
    _instance = None  # armazena a instância única

    def __new__(cls):
        if cls._instance is None:
            # Cria a instância uma única vez
            cls._instance = super(OcrImage, cls).__new__(cls)
        return cls._instance

    def __init__(
                self, 
                bin_tess: ocr.BinTesseract = ocr.BinTesseract(), *,
                lib_ocr: ocr.LibOcr = ocr.LibOcr.PYTESSERACT,
            ):
        # Evita reexecutar __init__ em chamadas subsequentes
        if not hasattr(self, "_initialized"):
            super().__init__(bin_tess, lib_ocr=lib_ocr)
            self._initialized = True


def update_column_table(tb: TableDocuments, *, name: ColumnsTable, new_value: str) -> TableDocuments:
    col = tb.get_column(name)
    for idx, v in enumerate(col):
        col[idx] = new_value
    tb[name] = col
    return tb


def concat_tables(list_map: list[TableDocuments]) -> TableDocuments:
    if len(list_map) < 1:
        return TableDocuments.create_void_dict()
    _columns: HeadValues = list_map[0].columns
    list_values: list[ListColumnBody] = []
    text_table: TableDocuments
    col: ListColumnBody
    i: HeadCell

    for i in _columns:
        list_values.append(
            ListColumnBody(i, ListString([]))
        )
    for text_table in list_map:
        for col in list_values:
            col.extend(
                text_table[col.col_name]
            )
    final_tb = TableDocuments(list_values)
    col_idx = final_tb[sheet.ColumnsTable.KEY]
    for idx, v in enumerate(col_idx):
        col_idx[idx] = f'{idx}'
    final_tb[sheet.ColumnsTable.KEY] = col_idx
    return final_tb


def create_table_from_dict(data: dict[str, sheet.ListColumnBody]) -> sheet.TableDocuments:
    _values: list[sheet.ListColumnBody] = []
    for _k in data.keys():
        _values.append(data[_k])
    return sheet.TableDocuments(_values)


def create_tb_from_names(files: list[sp.File]) -> list[TableDocuments]:
    values: list[TableDocuments] = []
    for f in files:
        tb = TableDocuments.create_void_dict()
        tb[sheet.ColumnsTable.TEXT.value].append(f.name())
        tb[sheet.ColumnsTable.FILETYPE.value].append(f.extension())
        tb[sheet.ColumnsTable.FILE_PATH.value].append(f.absolute())
        tb[sheet.ColumnsTable.FILE_NAME.value].append(f.basename())
        tb[sheet.ColumnsTable.KEY.value].append('0')
        tb[sheet.ColumnsTable.NUM_PAGE.value].append('nan')
        tb[sheet.ColumnsTable.NUM_LINE.value].append('1')
        tb[sheet.ColumnsTable.DIR.value].append(f.dirname())
        values.append(tb)
    return values


def read_image(img: cs.ImageObject, recognize: ocr.RecognizeImage = OcrImage()) -> TableDocuments:
    txt_image = recognize.image_to_string(img)
    try:
        tb = TableDocuments.create_from_values(
            txt_image.split('\n'),
            file_path=img.metadata.file_path,
            dir_path=img.metadata.dir_path,
            file_type=img.metadata.extension,
        )
    except Exception as err:
        print('---------------------------------------------')
        print(f'DEBUG: falha ao tentar gerar a tabela de: {img.metadata.file_path}\n{err}')
        print('---------------------------------------------')
        return TableDocuments.create_void_dict()
    else:
        return tb


def read_document(
            document: cs.DocumentPdf,
            recognize: ocr.RecognizeImage = OcrImage(), *,
            pbar: sp.ProgressBarAdapter = sp.ProgressBarAdapter(),
            dpi: int = 200,
            func_read_image: Callable[[cs.ImageObject, Optional[ocr.RecognizeImage]], TableDocuments] = None,
        ) -> TableDocuments:
    """
    Aplicar OCR em documento PDF e retornar uma tabela
    dos textos presentes no documento.
    """
    if func_read_image is None:
        func_read_image = read_image
    list_tables: list[TableDocuments] = []
    text_progress = sp.TextProgress()
    text_progress.pbar = pbar
    text_progress.start_pbar()
    text_progress.pbar.update(0, 'Iniciando a extração da tabela PDF')

    convert = cs.ConvertPdfToImages.create(document)
    convert.set_pbar(pbar)
    images: list[cs.ImageObject] = convert.to_images(dpi=dpi)
    text_progress.total = len(images)
    text_progress.text = 'OCR PDF'

    for page_pdf_idx, img in enumerate(images):
        text_progress.set_update()
        current_tb: TableDocuments = func_read_image(img, recognize)
        if current_tb.length > 0:
            current_tb = update_column_table(
                current_tb, name=sheet.ColumnsTable.FILETYPE, new_value=document.metadata.extension
            )
            current_tb = update_column_table(
                current_tb, name=sheet.ColumnsTable.NUM_PAGE, new_value=f'{page_pdf_idx+1}'
            )
            list_tables.append(current_tb)
    text_progress.pbar.update(100, 'Extração finalizada!')
    text_progress.stop_pbar()
    return concat_tables(list_tables)



