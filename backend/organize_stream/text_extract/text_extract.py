#!/usr/bin/env python3
from __future__ import annotations
from typing import Callable, Optional
from io import BytesIO
from sheet_stream import TableDocuments, IterRows, ListItems
from organize_stream.utils import ocr, cs, sp, sheet
from organize_stream.type_utils import (
    NotifyTableExtract, TextProgress, DiskFile, KeyFiles, KeyWordsFileName,
)
from organize_stream.read import read_image, read_document, OcrImage, concat_tables
import pandas as pd


class DocumentTextExtract(NotifyTableExtract):
    """

    """

    def __init__(
        self,
        recognize_image: ocr.RecognizeImage = OcrImage(), *,
        dpi: int = 200,
        apply_threshold: bool = False,
        notify_observers: bool = True,
        func_read_image: Callable[[cs.ImageObject, Optional[ocr.RecognizeImage]], TableDocuments] = None,
    ):
        super().__init__()
        if func_read_image is None:
            self._func_read_image = read_image
        else:
            self._func_read_image = func_read_image

        self.__collection_tables: ListItems[TableDocuments] = ListItems()
        self.__collection_tables.set_list_type(TableDocuments)
        self.recognize_image: ocr.RecognizeImage = recognize_image
        self.apply_threshold: bool = apply_threshold
        self.notify_observers: bool = notify_observers
        self.dpi: int = dpi
        self.__count_idx: int = 0
        self.text_progress: TextProgress = TextProgress()
        self.text_progress.set_pbar(sp.ProgressBarAdapter())
        self._pbar = self.text_progress.get_pbar()

    @property
    def values(self) -> list[TableDocuments]:
        return self.__collection_tables

    @property
    def length(self) -> int:
        return self.__collection_tables.length

    @property
    def pbar(self) -> sp.ProgressBarAdapter:
        return self.text_progress.get_pbar()

    @pbar.setter
    def pbar(self, pbar: sp.ProgressBarAdapter) -> None:
        self.text_progress.set_pbar(pbar)

    @property
    def is_empty(self) -> bool:
        return len(self.__collection_tables) == 0

    def add_table(self, tb: TableDocuments) -> None:
        if not isinstance(tb, TableDocuments):
            print(f'DEBUG: Tabela inválida: {tb}')
            return
        if tb.length == 0:
            print(f'DEBUG: Tabela vazia: {tb}')
            return
        self.__collection_tables.append(tb)
        self.__count_idx += 1
        if self.notify_observers:
            self.send_notify(tb)

    def add_dir_pdf(self, dir_pdf: sp.Directory) -> None:
        """
        Iterar sobre os arquivos PDF de uma pasta, extrair a tabela/texto de
        cada documento com OCR e adicionar cada tabela a propriedade/lista desse objeto.
        """
        files: list[sp.File] = sp.InputFiles(dir_pdf).pdfs
        self.text_progress.total = len(files)
        self.text_progress.set_default_text('Extraindo texto de Documento')
        self.text_progress.start_pbar()
        for n, f in enumerate(files):
            self.add_document(f)
        self.text_progress.stop_pbar()

    def add_dir_image(self, dir_image: sp.Directory):
        files_images = sp.InputFiles(dir_image).images
        self.text_progress.total = len(files_images)
        self.text_progress.set_default_text('Extraindo texto de imagem')
        self.text_progress.start_pbar()
        for idx, f in enumerate(files_images):
            self.add_image(f)
        self.text_progress.stop_pbar()

    def add_image(self, image: cs.ImageObject | sp.File | bytes | BytesIO) -> None:
        if isinstance(image, cs.ImageObject):
            pass
        else:
            image = cs.ImageObject(image, lib_image=cs.LibImage.OPENCV)
        if self.apply_threshold:
            image.set_threshold_black()
        self.add_table(self._func_read_image(image, self.recognize_image))

    def add_document(self, document: cs.DocumentPdf | sp.File | bytes | BytesIO) -> None:
        if isinstance(document, cs.DocumentPdf):
            pass
        elif isinstance(document, bytes):
            document = cs.DocumentPdf.create_from_bytes(BytesIO(document))
        else:
            document = cs.DocumentPdf(document)
        # Threshold
        if self.apply_threshold:
            _stream = cs.PdfStream()
            _stream.add_document(document)
            _stream.thresold()
            document = _stream.to_document()
        _tb = read_document(document, self.recognize_image, dpi=self.dpi, func_read_image=self._func_read_image)
        self.add_table(_tb)

    def to_table(self) -> TableDocuments:
        if len(self.__collection_tables) == 0:
            return TableDocuments.create_void_dict()
        return concat_tables(self.__collection_tables)

    def to_data(self) -> pd.DataFrame:
        return self.to_table().to_data().astype('str')

    def to_excel(self, file: sp.File) -> None:
        try:
            self.to_data().to_excel(file.absolute(), index=False)
        except Exception as e:
            print(f'Error: {e}')

    def read_image(self, image: DiskFile | cs.ImageObject) -> TableDocuments:
        if isinstance(image, cs.ImageObject):
            pass
        else:
            image = cs.ImageObject(image)
        return self._func_read_image(image, self.recognize_image)

    def read_document(self, document: DiskFile | cs.DocumentPdf) -> TableDocuments:
        if isinstance(document, cs.DocumentPdf):
            pass
        elif isinstance(document, bytes):
            document = cs.DocumentPdf.create_from_bytes(BytesIO(document))
        else:
            document = cs.DocumentPdf(document)
        return read_document(
            document,
            self.recognize_image,
            dpi=self.dpi,
            pbar=self.pbar,
            func_read_image=self._func_read_image
        )


