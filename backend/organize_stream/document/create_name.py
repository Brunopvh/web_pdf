#!/usr/bin/env python3
from __future__ import annotations

import os
import tempfile
from typing import Callable
from io import BytesIO
from typing import Union
from sheet_stream import TableDocuments, ColumnsTable, ListItems, ListColumnBody
from organize_stream.type_utils import (
    FilterText, FilterData, DigitalizedDocument, EnumDigitalDoc,
    ObserverTableExtraction, DictKeyWordFiles, DiskFile,
    DictOriginInfo, DictOutputInfo, DictFileInfo
)
from organize_stream.find import FindNameInnerText, FindNameInnerData
from organize_stream.utils import (sp, cs)
from organize_stream.read import create_tb_from_names
from organize_stream.text_extract import DocumentTextExtract
from organize_stream.cartas import CartaCalculo, GenericDocument, FichaEpi
from organize_stream.erros import *
import shutil
import zipfile
import pandas as pd


def move_path_files(mv_items: DictKeyWordFiles, *, replace: bool = False) -> bool:
    if mv_items.get_origin_file() is None or mv_items.get_output_file() is None:
        return False
    if mv_items.get_origin_file().get_abspath() is None:
        return False
    if mv_items.get_output_file().get_abspath() is None:
        return False
    if not mv_items.get_origin_file().get_abspath().exists():
        print(f'PULANDO o arquivo não existe ... {mv_items.get_origin_file().get_abspath().absolute()}')
        return False

    _output_full_path = mv_items.get_output_file().get_abspath().absolute()
    if not replace:
        if mv_items.get_output_file().get_abspath().path.exists():
            _count = 0
            _output_name = mv_items.get_output_file().get_name()
            _output_ext = mv_items.get_output_file().get_extension()
            while os.path.exists(_output_full_path):
                _count += 1
                _new_name = f'{_output_name}-{_count}{_output_ext}'
                _output_full_path = os.path.join(
                    mv_items.get_output_file().get_abspath().dirname(), _new_name
                )
    try:
        shutil.move(mv_items.get_origin_file().get_abspath().absolute(), _output_full_path)
    except Exception as e:
        print(e)
        return False
    return True


def save_keyword_files(
            key_files: DictKeyWordFiles, out_dir: sp.Directory
        ) -> tuple[DictFileInfo, DictOutputInfo | None, bool]:
    """
        Salva os bytes do arquivo destino no disco.
    """
    if key_files.get_output_file():
        raise InvalidSrcFile()
    if key_files.get_output_file().get_filename_with_extension() is None:
        return key_files.get_origin_file(), None, False
    if key_files.get_output_file().get_file_bytes() is None:
        return key_files.get_origin_file(), None, False

    out_dir.mkdir()
    if key_files.get_origin_file().get_file_bytes() is not None:
        return key_files.save_bytes(out_dir)
    elif key_files.get_output_file().get_file_bytes() is not None:
        return key_files.save_bytes(out_dir)
    return key_files.get_origin_file(), None, False


def _get_info_from_pdf(file: DiskFile | cs.DocumentPdf) -> tuple[DictOriginInfo, cs.DocumentPdf]:
    pdf_info = DictOriginInfo()
    if isinstance(file, cs.DocumentPdf):
        pdf_info.set_file_bytes(file.to_bytes().getvalue())
        pdf_info.set_extension('.pdf')
        pdf_info.set_filename_with_extension(f'{file.metadata.name}.pdf')
    elif isinstance(file, bytes):
        pdf_info.set_file_bytes(file)
        file = cs.DocumentPdf.create_from_bytes(BytesIO(file))
        pdf_info.set_extension(file.metadata.extension)
        pdf_info.set_filename_with_extension(f'{file.metadata.name}{file.metadata.extension}')
    elif isinstance(file, BytesIO):
        pdf_info.set_file_bytes(file.getvalue())
        file.seek(0)
        file = cs.DocumentPdf.create_from_bytes(file)
        pdf_info.set_extension(file.metadata.extension)
        pdf_info.set_filename_with_extension(f'{file.metadata.name}{file.metadata.extension}')
    elif isinstance(file, str):
        pdf_info.set_file_bytes(sp.File(file).path.read_bytes())
        file = cs.ImageObject.create_from_file(sp.File(file))
        pdf_info.set_extension(file.metadata.extension)
        pdf_info.set_filename_with_extension(f'{file.metadata.name}{file.metadata.extension}')
    elif isinstance(file, sp.File):
        pdf_info.set_file_bytes(file.path.read_bytes())
        pdf_info.set_extension(file.extension())
        pdf_info.set_filename_with_extension(file.basename())
        file = cs.DocumentPdf.create_from_file(file)

    if pdf_info.get_extension() == 'nan':
        pdf_info.set_extension(None)
    if pdf_info.get_filename_with_extension() == 'nan':
        pdf_info.set_filename_with_extension(None)
    if pdf_info.get_abspath() == 'nan':
        pdf_info.set_abspath(None)
    return pdf_info, file


def _get_info_from_img(file: DiskFile | cs.ImageObject) -> tuple[DictOriginInfo, cs.ImageObject]:
    img_info = DictOriginInfo()
    if isinstance(file, cs.ImageObject):
        img_info.set_file_bytes(file.to_bytes().getvalue())
        img_info.set_extension(file.metadata.extension)
        img_info.set_filename_with_extension(f'{file.metadata.name}{file.metadata.extension}')
    elif isinstance(file, bytes):
        img_info.set_file_bytes(file)
        file = cs.ImageObject.create_from_bytes(file)
        img_info.set_extension(file.metadata.extension)
        img_info.set_filename_with_extension(f'{file.metadata.name}{file.metadata.extension}')
    elif isinstance(file, BytesIO):
        img_info.set_file_bytes(file.getvalue())
        file.seek(0)
        file = cs.ImageObject.create_from_bytes(file.getvalue())
        img_info.set_extension(file.metadata.extension)
        img_info.set_filename_with_extension(f'{file.metadata.name}{file.metadata.extension}')
    elif isinstance(file, str):
        img_info.set_file_bytes(sp.File(file).path.read_bytes())
        file = cs.ImageObject.create_from_file(sp.File(file))
        img_info.set_extension(file.metadata.extension)
        img_info.set_filename_with_extension(f'{file.metadata.name}{file.metadata.extension}')
    elif isinstance(file, sp.File):
        img_info.set_abspath(file)
        img_info.set_file_bytes(file.path.read_bytes())
        img_info.set_extension(file.extension())
        img_info.set_filename_with_extension(file.basename())
        file = cs.ImageObject.create_from_file(file)

    if img_info.get_extension() == 'nan':
        img_info.set_extension(None)
    if img_info.get_filename_with_extension() == 'nan':
        img_info.set_filename_with_extension(None)
    if img_info.get_abspath() == 'nan':
        img_info.set_abspath(None)
    return img_info, file


class CreateFileNames(object):

    def __init__(
                self, *,
                extractor: DocumentTextExtract = DocumentTextExtract(),
                lib_digitalized: EnumDigitalDoc = EnumDigitalDoc.GENERIC,
                filters: FilterText = None,
                func_save_file: Callable[
                    [DictKeyWordFiles, sp.Directory], tuple[DictOriginInfo, DictOutputInfo | None, bool]
                ] = None,
                func_move_file: Callable[[DictKeyWordFiles], bool] = None,
            ):
        super().__init__()
        if func_save_file is None:
            self.func_save_file = save_keyword_files
        else:
            self.func_save_file = func_save_file

        if func_move_file is None:
            self.func_move_file = move_path_files
        else:
            self.func_move_file = func_move_file

        self.lib_digitalized: EnumDigitalDoc = lib_digitalized
        self.extractor: DocumentTextExtract = extractor
        self.extractor.apply_threshold = False
        self.filters = filters
        # Dicionário para gravar o status de exportação dos arquivos,
        # sendo que as chaves apontam para o arquivo de origem DynamicFile() e
        # os valores apontam para uma tupla, (DestFilePath, bool).

        self._dict_exported_info: dict[str, ListItems] = {
            'STATUS': ListItems(),
            'ORIGEM': ListItems(),
            'DESTINO': ListItems(),
        }
        self._list_key_filenames: ListItems[DictKeyWordFiles] = ListItems()
        self._list_key_filenames.set_list_type(DictKeyWordFiles)
        self.__temp_dir: sp.Directory = sp.Directory(tempfile.mkdtemp())

    def clear(self):
        self._dict_exported_info.clear()
        self._list_key_filenames.clear()

    def get_exported_files(self) -> dict[str, ListItems]:
        return self._dict_exported_info

    def get_list_key_files(self) -> ListItems[DictKeyWordFiles]:
        return self._list_key_filenames

    def create_output_info(self, tb: TableDocuments) -> DictOutputInfo | None:
        """
        Recebe uma tabela e retorna um dicionário de chave/valor com os dados
        do arquivo de origem e destino, incluindo extensão de arquivo.

        As informações do arquivo de origem são do tipo: DiskOriginInfo
        enquanto as informações do arquivo de destino são do tipo: DiskOutputInfo

        Tais valores podem ser nulos ou vazios se TableDocuments.length for igual 0.
        """
        if tb.length == 0:
            # raise TableFileEmptyError('A tabela de arquivos não pode estar vazia.')
            return None

        _doc: DigitalizedDocument
        if self.lib_digitalized == EnumDigitalDoc.GENERIC:
            _doc = GenericDocument(tb, filters=self.filters)
        elif self.lib_digitalized == EnumDigitalDoc.CARTA_CALCULO:
            _doc = CartaCalculo.create(tb)
        elif self.lib_digitalized == EnumDigitalDoc.EPI:
            _doc = FichaEpi.create(tb)
        else:
            raise InvalidTDigitalizedDocument(f'{__class__.__name__} Documento inválido: {self.lib_digitalized}')

        output_info = DictOutputInfo()
        # Proteger o objeto gerado contra valores de str padrão.
        filename_str = _doc.get_output_name_str()
        src_extension = _doc.extension_file
        if (filename_str is None) or (filename_str == 'nan') or (filename_str == ''):
            print(
                f'{__class__.__name__} Falha, o documento digitalizado não gerou um nome de saída =>> {tb.get_row(0)}'
                )
            return None
        if (src_extension is None) or (src_extension == '') and (src_extension == 'nan'):
            print(
                f'''
                    {__class__.__name__} Falha, a tabela não possui extensão de arquivo na coluna:
                    {ColumnsTable.FILETYPE.value} =>> {tb.get_column(ColumnsTable.FILETYPE.value)}
                '''
                )
            return None
        
        output_info.set_extension(src_extension)
        output_info.set_name(filename_str)
        output_info.set_filename_with_extension(f'{filename_str}{src_extension}')
        return output_info

    def save_file_keyword(
                self, key_word_file: DictKeyWordFiles, out_dir: sp.Directory
            ) -> tuple[DictOriginInfo, DictOutputInfo, bool]:
        """
        Recebe um objeto DictKeyWordFiles() e um diretório para salvar o arquivo de origem
        no destino padronizado.

        Apenas os bytes são salvos no destino, sem mover os arquivos originais.
        """
        # Salvar/Exportar os bytes do arquivo destino.
        _status: tuple[DictOriginInfo, DictOutputInfo, bool] = self.func_save_file(key_word_file, out_dir)
        self._add_log_status(key_word_file, _status[2])
        return _status

    def _add_log_status(self, key_word_file: DictKeyWordFiles, status: bool) -> None:
        # Gravar o status da operação
        src = None
        dest = None
        if key_word_file.get_origin_file() is not None:
            src = key_word_file.get_origin_file().get_filename_with_extension()
        if key_word_file.get_output_file() is not None:
            dest = key_word_file.get_output_file().get_filename_with_extension()
        self._dict_exported_info['ORIGEM'].append(src)
        self._dict_exported_info['DESTINO'].append(dest)
        self._dict_exported_info['STATUS'].append(status)

    def move_file_keyword(
                self, key_word_file: DictKeyWordFiles
            ) -> tuple[DictOriginInfo, DictOutputInfo, bool]:
        """
        Recebe um objeto DictKeyWordFiles() e move o arquivo de origem para o destino padronizado.
        """
        if key_word_file.get_output_file().get_abspath() is None:
            print(f'{__class__.__name__} DEBUG: o arquivo destino é nulo')
            self._add_log_status(key_word_file, False)
            return key_word_file.get_origin_file(), key_word_file.get_output_file(), False
        if key_word_file.get_origin_file().get_abspath() is None:
            print(f'{__class__.__name__} DEBUG: o arquivo origem é nulo')
            self._add_log_status(key_word_file, False)
            return key_word_file.get_origin_file(), key_word_file.get_output_file(), False

        _status: bool = self.func_move_file(key_word_file)
        # Gravar o status da operação
        self._add_log_status(key_word_file, _status)
        return key_word_file.get_origin_file(), key_word_file.get_output_file(), _status

    def read_image(self, file: DiskFile | cs.ImageObject) -> DictKeyWordFiles:
        """
            Gera um objeto DictKeyWordFiles() que pode ser exportado/salvo no disco posteriormente.
        """
        image_info: tuple[DictOriginInfo, cs.ImageObject] = _get_info_from_img(file)
        tb = self.extractor.read_image(image_info[1])
        if tb.get_column(ColumnsTable.FILETYPE).length == 0:
            _new = [image_info[0].get_extension()] * tb.get_column(ColumnsTable.TEXT).length
            tb.set_column(ListColumnBody(ColumnsTable.FILETYPE.value, _new))
            
        dest_info: DictOutputInfo | None = self.create_output_info(tb)
        __kw = DictKeyWordFiles()
        __kw.set_origin_file(image_info[0])
        if dest_info is not None:
            __kw.set_output_file(dest_info)
        else:
            __kw.set_output_file(DictOutputInfo())
        return __kw

    def read_document(self, file: DiskFile | cs.DocumentPdf) -> DictKeyWordFiles:
        """
            Gera um KeyWordsFileName que pode ser exportado/salvo no disco posteriormente.
        """
        pdf_info: tuple[DictOriginInfo, cs.DocumentPdf] = _get_info_from_pdf(file)
        __kw = DictKeyWordFiles()
        __kw.set_origin_file(pdf_info[0])
        tb = self.extractor.read_document(pdf_info[1])
        if tb.get_column(ColumnsTable.FILETYPE).length == 0:
            _new = [pdf_info[0].get_extension()] * tb.get_column(ColumnsTable.TEXT).length
            tb.set_column(ListColumnBody(ColumnsTable.FILETYPE.value, _new))
        
        dest_info = self.create_output_info(tb)
        if dest_info is not None:
            __kw.set_output_file(dest_info)
        else:
            __kw.set_output_file(DictOutputInfo())
        return __kw

    def rename_image(self, image: sp.File, output_dir: sp.Directory):
        """
        Extrai o texto de uma imagem e renomeia conforme o padrão do documento informado nesse objeto.
        """
        __kw_im: DictKeyWordFiles = self.read_image(image)
        __kw_im.set_output_dir(output_dir)
        self.move_file_keyword(__kw_im)

    def rename_document(
            self, document: sp.File, output_dir: sp.Directory
    ) -> None:
        """
        Extrai o texto de um PDF e renomeia conforme o padrão do documento informado nesse objeto.
        """
        __kw_pdf: DictKeyWordFiles = self.read_document(document)
        __kw_pdf.set_output_dir(output_dir)
        self.move_file_keyword(__kw_pdf)

    def add_image(self, image: DiskFile | cs.ImageObject):
        __k_img = self.read_image(image)
        self._list_key_filenames.append(__k_img)

    def add_document(self, document: DiskFile | cs.DocumentPdf):
        __k_doc: DictKeyWordFiles = self.read_document(document)
        self._list_key_filenames.append(__k_doc)

    def add_disk_file(self, disk_file: DictFileInfo):
        if disk_file.get_extension() is None:
            raise DiskFileInvalidError(f'Use: Adicione uma extensão de arquivo em DiskFileInfo')
        if disk_file.get_file_bytes() is None:
            raise DiskFileInvalidError(f'Use: Adicione bytes ao DiskFileInfo')
        
        key_info = DictKeyWordFiles()
        key_info.set_origin_file(disk_file)
        tb: TableDocuments = None
        if disk_file.get_extension() in ['.png', '.jpg', '.jpeg', '.svg']:
            image_obj = cs.ImageObject.create_from_bytes(disk_file.get_file_bytes())
            tb = self.extractor.read_image(image_obj)
        elif disk_file.get_extension() in ['.pdf']:
            doc_pdf = cs.DocumentPdf.create_from_bytes(BytesIO(disk_file.get_file_bytes()))
            tb = self.extractor.read_document(doc_pdf)
        else:
            print(f'{__class__.__name__} DEBUG: Falha ao tentar identificar o documento =>> {disk_file.get_name()}')
            return
                
        if tb is None:
            print(f'{__class__.__name__} Arquivo NÃO adiconado A tabela é nula *** {disk_file.get_name()}')
            return
        if tb.length == 0:
            print(f'{__class__.__name__} Arquivo NÃO adiconado a tabela gerada está vazia => {disk_file.get_name()}')
            return
        
        # Antes de gerar o dicionário com as informações de destino, precisamos adicionar
        # A extensão de arquivo a tabela gerada.
        _new = [disk_file.get_extension()] * tb.get_column(ColumnsTable.TEXT.value).length
        tb.set_column(ListColumnBody(ColumnsTable.FILETYPE, _new))
        
        dict_output: DictOutputInfo | None = self.create_output_info(tb)
        if dict_output is None:
            print(f'{__class__.__name__} Falha ao tentar gerar o nome do arquivo de destino => {disk_file.get_name()}')
            return
        key_info.set_output_file(dict_output)
        self._list_key_filenames.append(key_info)
            
    def export_new_filenames(self, output_dir: sp.Directory) -> None:
        """
        Salva os bytes de todos os documentos processados.
        """
        total = self._list_key_filenames.length
        for num, k_file in enumerate(self._list_key_filenames):
            self.extractor.pbar.update(
                ((num + 1) / total) * 100,
                f'{num + 1}/{total} Exportando arquivos',
            )
            self.save_file_keyword(k_file, output_dir)

    def export_log_actions(self) -> pd.DataFrame:
        __data: dict[str, list[str]] = {
            'STATUS': [],
            'ARQUIVO_ORIGEM': [],
            'NOVO_NOME': [],

        }
        for num, item in enumerate(self._dict_exported_info['STATUS']):
            value = "FALHA" if not item else "SUCESSO"
            __data['STATUS'].append(str(value))
            __data['ARQUIVO_ORIGEM'].append(self._dict_exported_info["ORIGEM"][num])
            __data['NOVO_NOME'].append(self._dict_exported_info["DESTINO"][num])
        __df = pd.DataFrame(__data)
        return __df.astype('str')

    def export_new_files_to_zip(self) -> BytesIO | None:
        """
        Renomeia os arquivos e retorna BytesIO() com o conteúdo final zipado.
        """
        if self._list_key_filenames.length == 0:
            print(f'DEBUG: {__class__.__name__} nenhuma tabela disponível para exportar!')
            return None
        print(f'Exportando: {self._list_key_filenames.length} arquivos')

        zip_buffer = BytesIO()
        key_file: DictKeyWordFiles
        try:
            with zipfile.ZipFile(zip_buffer, "w") as zipf:
                for key_file in self._list_key_filenames:
                    final_bytes = None
                    if key_file.get_output_file().get_file_bytes() is not None:
                        final_bytes = key_file.get_output_file().get_file_bytes()
                    elif key_file.get_origin_file().get_file_bytes() is not None:
                        final_bytes = key_file.get_origin_file().get_file_bytes()
                    if final_bytes is None:
                        self._add_log_status(key_file, False)
                        print(f'[PULANDO] ... bytes nulos {key_file.get_origin_file().get_filename_with_extension()}')
                        continue
                    if key_file.get_output_file().get_filename_with_extension() is None:
                        self._add_log_status(key_file, False)
                        print(
                            f'Erro: nome destino é nulo {key_file.get_origin_file().get_filename_with_extension()}'
                        )
                        continue

                    dest_file_name: str = key_file.get_output_file().get_filename_with_extension()
                    zipf.writestr(dest_file_name, final_bytes)
                    self._add_log_status(key_file, True)
        except Exception as err:
            print(f'{__class__.__name__}: {err}')
            return None
        else:
            zip_buffer.seek(0)
            return zip_buffer


class ExtractName(ObserverTableExtraction):

    def __init__(self, output_dir: sp.Directory, *, filters: FilterText = None):
        super().__init__()
        self._count: int = 0
        self.output_dir: sp.Directory = output_dir
        self.pbar: sp.ProgressBarAdapter = sp.ProgressBarAdapter()
        self.max_char: int = 90
        self.upper_case: bool = True
        self.save_tables: bool = True
        self.filters: FilterText = filters
        self.extractor: DocumentTextExtract = DocumentTextExtract()
        self.extractor.apply_threshold = False
        self.extractor.add_observer(self)

    @property
    def output_dir_tables(self) -> sp.Directory:
        return self.output_dir.concat('Tabelas', create=True)

    def _show_error(self, txt: str):
        print()
        self.pbar.update_text(f'{__class__.__name__} {txt}')

    def add_table(self, tb: TableDocuments):
        pass

    def export_tables(self, tb: TableDocuments) -> None:
        if not self.save_tables:
            return
        origin_name = tb.get_column(ColumnsTable.FILE_NAME)[0]
        output_path = self.output_dir_tables.join_file(f'{origin_name}.xlsx')
        if isinstance(output_path, sp.File):
            #print(f'DEBUG: Exportando ... {output_path.basename()}')
            tb.to_data().to_excel(output_path.absolute(), index=False)

    def export_final_table(self):
        if not self.save_tables:
            return
        self.extractor.to_excel(self.output_dir_tables.join_file('data.xlsx'))

    def receive_notify(self, notify: TableDocuments) -> None:
        pass

    def move_digitalized_doc(self, tb: TableDocuments) -> None:
        pass


class ExtractNameInnerText(ExtractName):
    """
    Mover/Renomear arquivos de acordo com padrões de texto presentes
    nos documentos/imagens.

    O padrão de texto a ser filtrado deve ser criado no objeto FilterText(). Se desejar
    filtrar mais de uma ocorrência nos documentos/imagens, separe as ocorrências com um '|'

    """

    def __init__(
            self,
            output_dir: sp.Directory, *,
            lib_digitalized: EnumDigitalDoc = EnumDigitalDoc.GENERIC,
            filters: FilterText = None,
    ):
        super().__init__(output_dir, filters=filters)
        self.lib_digitalized: EnumDigitalDoc = lib_digitalized
        self.name_finder: FindNameInnerText = FindNameInnerText(self.output_dir)

    def receive_notify(self, notify: TableDocuments) -> None:
        self._count += 1
        self.move_digitalized_doc(notify)
        self.export_tables(notify)

    def add_table(self, tb: TableDocuments):
        self.move_digitalized_doc(tb)
        self.export_tables(tb)

    def move_digitalized_doc(self, tb: TableDocuments) -> None:
        """
        Mover/Renomear arquivos de acordo com padrões de texto presentes
        nos documentos/imagens.
        """
        dg: DigitalizedDocument
        if self.lib_digitalized == EnumDigitalDoc.GENERIC:
            if self.filters is None:
                print(f'DEBUG: {__class__.__name__} Falha ... o filtro está vazio.')
                return
            dg = GenericDocument(tb, filters=self.filters)
        elif self.lib_digitalized == EnumDigitalDoc.CARTA_CALCULO:
            dg = CartaCalculo.create(tb)
        elif self.lib_digitalized == EnumDigitalDoc.EPI:
            dg = FichaEpi.create(tb)
        else:
            raise InvalidTDigitalizedDocument()
        new_names: DictKeyWordFiles = self.name_finder.get_new_name(dg)
        move_path_files(new_names, replace=False)


class ExtractNameInnerData(ExtractName):
    """
        Organizar os arquivos com base nos dados de uma tabela/DataFrame
    """

    def __init__(self, output_dir: sp.Directory, *, filters: FilterData = None):
        super().__init__(output_dir, filters=None)
        self.filter_data: FilterData = filters
        self.name_inner_data: FindNameInnerData = FindNameInnerData(self.output_dir, filters=self.filter_data)

    def receive_notify(self, notify: TableDocuments) -> None:
        self._count += 1
        self.move_digitalized_doc(notify)
        self.export_tables(notify)

    def add_table(self, tb: TableDocuments):
        self.move_digitalized_doc(tb)
        self.export_tables(tb)

    def move_digitalized_doc(self, tb: TableDocuments) -> None:
        mv_items = self.name_inner_data.get_new_name(
            GenericDocument(tb, filters=None)
        )
        move_path_files(mv_items, replace=False)

    def move_where_math_filename(self, files: list[sp.File]) -> None:
        """

        """
        values: list[TableDocuments] = create_tb_from_names(files)
        for current_tb in values:
            mv_items = self.name_inner_data.get_new_name(
                GenericDocument(current_tb, filters=None)
            )
            move_path_files(mv_items, replace=False)
