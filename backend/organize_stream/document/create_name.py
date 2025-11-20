#!/usr/bin/env python3
from __future__ import annotations
import tempfile
from typing import Callable
from io import BytesIO
from typing import Union
from sheet_stream import TableDocuments, ColumnsTable, ListItems
from organize_stream.type_utils import (
    FilterText, FilterData, DigitalizedDocument, LibDigitalized,
    ObserverTableExtraction, KeyWordsFileName, DiskFile,
    DiskOriginInfo, DiskOutputInfo, DiskFileInfo
)
from organize_stream.find import (
    NameFinderInnerText, NameFinderInnerData, OriginFileName, DestFilePath
)
from organize_stream.utils import (sp, cs)
from organize_stream.read import create_tb_from_names
from organize_stream.text_extract import DocumentTextExtract
from organize_stream.cartas import CartaCalculo, GenericDocument, FichaEpi
from organize_stream.erros import *
import shutil
import zipfile
import pandas as pd

FindItem = Union[str, list[str]]


def move_list_files(
        mv_items: dict[str, list[sp.File]], *,
        replace: bool = False
) -> None:
    total_file = len(mv_items['src'])
    for idx, file in enumerate(mv_items['src']):
        output_path: sp.File = mv_items['dest'][idx]
        if not file.exists():
            print(f'[PULANDO]: {idx + 1} Arquivo não encontrado {file.absolute()}')
        if output_path.exists():
            if not replace:
                _count = 0
                origin_name = output_path.name_absolute()
                origin_ext = output_path.extension()
                while output_path.exists():
                    _count += 1
                    new_name = f'{origin_name}-{_count}{origin_ext}'
                    output_path = sp.File(new_name)
                del origin_name
                del origin_ext
        print(f'Movendo: {idx + 1}/{total_file} {file.absolute()}')
        try:
            shutil.move(file.absolute(), output_path.absolute())
        except Exception as e:
            print(f'{e}')
        del output_path


def move_path_files(
        mv_items: dict[OriginFileName, DestFilePath], *,
        replace: bool = False
) -> None:
    for _k in mv_items:
        output_path = mv_items[_k]
        if not _k.exists():
            print(f'[PULANDO O ARQUIVO NÃO EXISTE]: {_k.basename()}')
        if not replace:
            _count = 0
            origin_name: str = output_path.name_absolute()
            origin_ext = output_path.extension()
            while output_path.exists():
                _count += 1
                new_output_name: str = f'{origin_name}-{_count}{origin_ext}'
                output_path = sp.File(new_output_name)
            del origin_name
            del origin_ext
        try:
            shutil.move(_k.absolute(), output_path.absolute())
        except Exception as e:
            print(e)


def save_key_word_filename(
        key_word_file: KeyWordsFileName,
        out_dir: sp.Directory
) -> tuple[DiskFileInfo, DiskOutputInfo | None, bool]:
    """
    SALVAR/MOVER o arquivo nomeado no disco e retorna Tuple contendo a sequência:
        - arquivo original, arquivo salvo no disco e booleano(sucesso ou falha na operação).
    Se o terceiro elemento for False, significa que a operação falhou.

    Se o arquivo origem (SRC) for bytes/BytesIO() os dados serão salvos no diretório informado
    sem alterar os arquivos de origem, se a origem for File()/str os arquivos serão movidos para
    o novo diretório.

    @rtype: tuple[DynamicFile, DestFilePath | None, bool]
    @type key_word_file: KeyWordsFileName
    @type out_dir: sp.Directory

    :rtype: Tuple[DynamicFile, DestFilePath | None, bool]
    :param out_dir: Diretório onde o arquivo de saída será gravado.
    :param key_word_file: Objeto/dicionário com os dados dos arquivos de origem e destino.
    """
    if ((key_word_file.get_origin_file().get_file_bytes() is None) and
            (key_word_file.get_origin_file().get_abspath() is None)):
        raise InvalidSrcFile()
    if key_word_file.get_output_file().get_filename() is None:
        return key_word_file.get_origin_file(), None, False

    out_dir.mkdir()
    if key_word_file.get_origin_file().get_file_bytes() is not None:
        # Salvar os bytes no disco.
        return key_word_file.save(out_dir)
    elif key_word_file.get_origin_file().get_abspath() is not None:
        # Mover o arquivo no disco.
        return key_word_file.move(out_dir)
    return key_word_file.get_origin_file(), None, False


def _get_info_from_pdf(file: DiskFile | cs.DocumentPdf) -> tuple[DiskOriginInfo, cs.DocumentPdf]:
    pdf_info = DiskOriginInfo()
    if isinstance(file, cs.DocumentPdf):
        pdf_info.set_file_bytes(file.to_bytes().getvalue())
        pdf_info.set_extension(file.metadata.extension)
        pdf_info.set_filename(f'{file.metadata.name}{file.metadata.extension}')
    elif isinstance(file, bytes):
        pdf_info.set_file_bytes(file)
        file = cs.DocumentPdf.create_from_bytes(BytesIO(file))
        pdf_info.set_extension(file.metadata.extension)
        pdf_info.set_filename(f'{file.metadata.name}{file.metadata.extension}')
    elif isinstance(file, BytesIO):
        pdf_info.set_file_bytes(file.getvalue())
        file.seek(0)
        file = cs.DocumentPdf.create_from_bytes(file)
        pdf_info.set_extension(file.metadata.extension)
        pdf_info.set_filename(f'{file.metadata.name}{file.metadata.extension}')
    elif isinstance(file, str):
        pdf_info.set_file_bytes(sp.File(file).path.read_bytes())
        file = cs.ImageObject.create_from_file(sp.File(file))
        pdf_info.set_extension(file.metadata.extension)
        pdf_info.set_filename(f'{file.metadata.name}{file.metadata.extension}')
    elif isinstance(file, sp.File):
        pdf_info.set_file_bytes(file.path.read_bytes())
        pdf_info.set_extension(file.extension())
        pdf_info.set_filename(file.basename())
        file = cs.DocumentPdf.create_from_file(file)

    if pdf_info.get_extension() == 'nan':
        pdf_info.set_extension(None)
    if pdf_info.get_filename() == 'nan':
        pdf_info.set_filename(None)
    if pdf_info.get_abspath() == 'nan':
        pdf_info.set_abspath(None)
    return pdf_info, file


def _get_info_from_img(file: DiskFile | cs.ImageObject) -> tuple[DiskOriginInfo, cs.ImageObject]:
    img_info = DiskOriginInfo()
    if isinstance(file, cs.ImageObject):
        img_info.set_file_bytes(file.to_bytes().getvalue())
        img_info.set_extension(file.metadata.extension)
        img_info.set_filename(f'{file.metadata.name}{file.metadata.extension}')
    elif isinstance(file, bytes):
        img_info.set_file_bytes(file)
        file = cs.ImageObject.create_from_bytes(file)
        img_info.set_extension(file.metadata.extension)
        img_info.set_filename(f'{file.metadata.name}{file.metadata.extension}')
    elif isinstance(file, BytesIO):
        img_info.set_file_bytes(file.getvalue())
        file.seek(0)
        file = cs.ImageObject.create_from_bytes(file.getvalue())
        img_info.set_extension(file.metadata.extension)
        img_info.set_filename(f'{file.metadata.name}{file.metadata.extension}')
    elif isinstance(file, str):
        img_info.set_file_bytes(sp.File(file).path.read_bytes())
        file = cs.ImageObject.create_from_file(sp.File(file))
        img_info.set_extension(file.metadata.extension)
        img_info.set_filename(f'{file.metadata.name}{file.metadata.extension}')
    elif isinstance(file, sp.File):
        img_info.set_file_bytes(file.path.read_bytes())
        img_info.set_extension(file.extension())
        img_info.set_filename(file.basename())
        file = cs.ImageObject.create_from_file(file)

    if img_info.get_extension() == 'nan':
        img_info.set_extension(None)
    if img_info.get_filename() == 'nan':
        img_info.set_filename(None)
    if img_info.get_abspath() == 'nan':
        img_info.set_abspath(None)
    return img_info, file


class CreateNewFile(object):

    def __init__(
            self,
            extractor: DocumentTextExtract = DocumentTextExtract(),
            lib_digitalized: LibDigitalized = LibDigitalized.GENERIC,
            filters: FilterText = None,
            func_save_file: Callable[
                [KeyWordsFileName, sp.Directory], tuple[DiskOriginInfo, DiskOutputInfo | None, bool]
            ] = None,
    ):
        super().__init__()
        if func_save_file is None:
            self.func_save_file = save_key_word_filename
        else:
            self.func_save_file = func_save_file

        self.lib_digitalized: LibDigitalized = lib_digitalized
        self.extractor: DocumentTextExtract = extractor
        self.extractor.apply_threshold = False
        self.filters = filters
        # Dicionário para gravar o status de exportação dos arquivos,
        # sendo que as chaves apontam para o arquivo de origem DynamicFile() e
        # os valores apontam para uma tupla, (DestFilePath, bool).
        _list_status = ListItems()
        _list_origin = ListItems()
        _list_dest = ListItems()

        self.__exported_files: dict[str, ListItems] = {
            'STATUS': _list_status,
            'ORIGEM': _list_origin,
            'DESTINO': _list_dest,
        }
        self.__list_key_files: ListItems[KeyWordsFileName] = ListItems()
        self.__list_key_files.set_list_type(KeyWordsFileName)
        self.__temp_dir: sp.Directory = sp.Directory(tempfile.mkdtemp())

    def clear(self):
        self.__exported_files.clear()
        self.__list_key_files.clear()

    def get_exported_files(self) -> dict[str, ListItems]:
        return self.__exported_files

    def get_list_key_files(self) -> ListItems[KeyWordsFileName]:
        return self.__list_key_files

    def read_image(self, file: DiskFile | cs.ImageObject) -> KeyWordsFileName:
        """
            Gera um KeyWordsFileName que pode ser exportado/salvo no disco posteriormente.
        """
        image_info: tuple[DiskOriginInfo, cs.ImageObject] = _get_info_from_img(file)
        dest_info = self.create_output_info(self.extractor.read_image(image_info[1]))
        __kw = KeyWordsFileName()
        __kw.set_origin_file(image_info[0])
        __kw.set_output_file(dest_info)
        return __kw

    def read_document(self, file: DiskFile | cs.DocumentPdf) -> KeyWordsFileName:
        """
            Gera um KeyWordsFileName que pode ser exportado/salvo no disco posteriormente.
        """
        pdf_info: tuple[DiskOriginInfo, cs.DocumentPdf] = _get_info_from_pdf(file)
        dest_info = self.create_output_info(self.extractor.read_document(pdf_info[1]))
        __kw = KeyWordsFileName()
        __kw.set_origin_file(pdf_info[0])
        __kw.set_output_file(dest_info)
        return __kw

    def create_output_info(self, tb: TableDocuments) -> DiskOutputInfo | None:
        """
        Recebe uma tabela e retorna um dicionário de chave/valor com os dados
        do arquivo de origem e destino, incluindo extensão de arquivo.

        As informações do arquivo de origem são do tipo: DiskOriginInfo
        enquanto as informações do arquivo de destino são do tipo: DiskOutputInfo

        Tais valores podem ser nulos ou vazios se TableDocuments.length for igual 0.
        """

        if tb.length == 0:
            raise TableFileEmptyError('A tabela de arquivos não pode estar vazia.')
        
        output_info = DiskOutputInfo()
        _doc: DigitalizedDocument
        if self.lib_digitalized == LibDigitalized.GENERIC:
            _doc = GenericDocument(tb, filters=self.filters)
        elif self.lib_digitalized == LibDigitalized.CARTA_CALCULO:
            _doc = CartaCalculo.create(tb)
        elif self.lib_digitalized == LibDigitalized.EPI:
            _doc = FichaEpi.create(tb)
        else:
            raise InvalidTDigitalizedDocument(f'{__class__.__name__} Documento inválido: {self.lib_digitalized}')
        
        # Proteger o objeto gerado contra valores de str padrão.
        filename_str = _doc.get_output_name_str()
        src_extension = _doc.extension_file
        if (filename_str is None) or (filename_str == 'nan') or (filename_str == ''):
            print(f'Novo nome não gerado ... {tb.get_row(0)}')
            return None
        if (src_extension is None) or (src_extension == '') and (src_extension == 'nan'):
            src_extension = tb.get_column(ColumnsTable.FILETYPE).first
        if (src_extension is not None) and (src_extension != '') and (src_extension != 'nan'):
            output_info.set_extension(src_extension)
        output_info.set_filename(f'{filename_str}{output_info.get_extension()}')
        return output_info

    def _save_file_keyword(
            self, key_word_file: KeyWordsFileName, out_dir: sp.Directory
    ) -> tuple[DiskOriginInfo, DiskOutputInfo, bool]:
        """
        Recebe um objeto KeyWordsFileName() e um diretório para salvar o arquivo de origem
        no destino padronizado.

        Se o arquivo de origem for File()/str serão movidos, se não
        serão salvos sem alterar os arquivos fonte.
        """
        _status: tuple[DiskOriginInfo, DiskOutputInfo, bool] = self.func_save_file(key_word_file, out_dir)
        self.__exported_files['ORIGEM'].append(
            _status[0].get_filename() if _status[1] is not None else None
        )
        self.__exported_files['DESTINO'].append(
            _status[1].get_filename() if _status[1] is not None else None
        )
        self.__exported_files['STATUS'].append(_status[2])
        return _status

    def rename_image(self, image: DiskFile | cs.ImageObject, output_dir: sp.Directory):
        """
        Extrai o texto de uma imagem e renomeia conforme o padrão do documento informado nesse objeto.
        """
        __kw_im: KeyWordsFileName = self.read_image(image)
        self._save_file_keyword(__kw_im, output_dir)

    def rename_document(
            self, document: DiskFile | cs.DocumentPdf, output_dir: sp.Directory
    ) -> None:
        """
        Extrai o texto de um PDF e renomeia conforme o padrão do documento informado nesse objeto.
        """
        __kw_pdf: KeyWordsFileName = self.read_document(document)
        self._save_file_keyword(__kw_pdf, output_dir)

    def add_image(self, image: DiskFile | cs.ImageObject):
        __k_img = self.read_image(image)
        self.__list_key_files.append(__k_img)

    def add_document(self, document: DiskFile | cs.DocumentPdf):
        __k_doc: KeyWordsFileName = self.read_document(document)
        self.__list_key_files.append(__k_doc)

    def add_disk_file(self, disk_file: DiskFileInfo):
        if not isinstance(disk_file, DiskFileInfo):
            raise DiskFileInvalidError(f'Use: DiskFileInfo(), não {type(disk_file)}')
        if disk_file.get_extension() is None:
            raise DiskFileInvalidError(f'Use: Adicione uma extensão de arquivo em DiskFileInfo')
        if disk_file.get_file_bytes() is None:
            raise DiskFileInvalidError(f'Use: Adicione bytes ao DiskFileInfo')
        
        key_info = KeyWordsFileName()
        key_info.set_origin_file(disk_file)
        tb: TableDocuments = None
        if disk_file.get_extension() in ['.png', '.jpg', '.jpeg', '.svg']:
            image_obj = cs.ImageObject.create_from_bytes(disk_file.get_file_bytes())
            tb = self.extractor.read_image(image_obj)
        elif disk_file.get_extension() in ['.pdf']:
            doc_pdf = cs.DocumentPdf.create_from_bytes(BytesIO(disk_file.get_file_bytes()))
            tb = self.extractor.read_document(doc_pdf)
                
        if tb is None:
            print(f'\nDEBUG: arquivo NÃO adiconado ... {disk_file.get_extension()}')
            return
        if tb.length == 0:
            print(f'\nDEBUG: arquivo NÃO adiconado, devido a tabela estar vazia')
            return
        output_info = self.create_output_info(tb)
        if output_info is not None:
            if output_info.get_extension() is None:
                ext = disk_file.get_extension()
                output_info.set_filename(f'{output_info.get_filename()}{ext}')
            key_info.set_output_file(output_info)
            self.__list_key_files.append(key_info)
            
    def export_new_files(self, output_dir: sp.Directory) -> None:
        total = self.__list_key_files.length
        for num, k_file in enumerate(self.__list_key_files):
            self.extractor.pbar.update(
                ((num + 1) / total) * 100,
                f'{num + 1}/{total} Exportando arquivos',
            )
            self._save_file_keyword(k_file, output_dir)

    def export_log_actions(self) -> pd.DataFrame:
        __data: dict[str, list[str]] = {
            'STATUS': [],
            'ARQUIVO_ORIGEM': [],
            'NOVO_NOME': [],

        }
        for num, item in enumerate(self.__exported_files['STATUS']):
            value = "FALHA" if not item else "SUCESSO"
            __data['STATUS'].append(str(value))
            __data['ARQUIVO_ORIGEM'].append(self.__exported_files["ORIGEM"][num])
            __data['NOVO_NOME'].append(self.__exported_files["DESTINO"][num])
        __df = pd.DataFrame(__data)
        return __df.astype('str')

    def export_keys_to_zip(self) -> BytesIO | None:
        """
        Renomeia os arquivos e retorna BytesIO() com o conteúdo final zipado.
        """
        if self.__list_key_files.length == 0:
            print(f'DEBUG: {__class__.__name__} nenhuma tabela disponível para exportar!')
            return None
        print(f'Exportando: {self.__list_key_files.length} arquivos')

        zip_buffer = BytesIO()
        key_file: KeyWordsFileName
        try:
            with zipfile.ZipFile(zip_buffer, "w") as zipf:
                for key_file in self.__list_key_files:
                    final_bytes = None
                    if key_file.get_output_file().get_file_bytes() is not None:
                        final_bytes = key_file.get_output_file().get_file_bytes()
                    elif key_file.get_origin_file().get_file_bytes() is not None:
                        final_bytes = key_file.get_origin_file().get_file_bytes()
                    if final_bytes is None:
                        self.__exported_files['STATUS'].append(False)
                        self.__exported_files['ORIGEM'].append(key_file.get_origin_file().get_filename())
                        self.__exported_files['DESTINO'].append(key_file.get_output_file().get_filename())
                        print(f'[PULANDO] ... bytes nulos {key_file.get_origin_file().get_filename()}')
                        continue
                    if key_file.get_output_file().get_filename() is None:
                        self.__exported_files['STATUS'].append(False)
                        self.__exported_files['ORIGEM'].append(key_file.get_origin_file().get_filename())
                        self.__exported_files['DESTINO'].append(key_file.get_output_file().get_filename())
                        print(f'[PULANDO] ... nome destino é nulo {key_file.get_origin_file().get_filename()}')
                        continue

                    dest_file_name: str = key_file.get_output_file().get_filename()
                    zipf.writestr(dest_file_name, final_bytes)
                    self.__exported_files['STATUS'].append(True)
                    self.__exported_files['ORIGEM'].append(key_file.get_origin_file().get_filename())
                    self.__exported_files['DESTINO'].append(key_file.get_output_file().get_filename())
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
            lib_digitalized: LibDigitalized = LibDigitalized.GENERIC,
            filters: FilterText = None,
    ):
        super().__init__(output_dir, filters=filters)
        self.lib_digitalized: LibDigitalized = lib_digitalized
        self.name_finder: NameFinderInnerText = NameFinderInnerText(self.output_dir)

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
        if self.lib_digitalized == LibDigitalized.GENERIC:
            if self.filters is None:
                print(f'DEBUG: {__class__.__name__} Falha ... o filtro está vazio.')
                return
            dg = GenericDocument(tb, filters=self.filters)
        elif self.lib_digitalized == LibDigitalized.CARTA_CALCULO:
            dg = CartaCalculo.create(tb)
        elif self.lib_digitalized == LibDigitalized.EPI:
            dg = FichaEpi.create(tb)
        else:
            raise InvalidTDigitalizedDocument()
        new_names: dict[OriginFileName, DestFilePath] = self.name_finder.get_new_name(dg)
        move_path_files(new_names, replace=False)


class ExtractNameInnerData(ExtractName):
    """
        Organizar os arquivos com base nos dados de uma tabela/DataFrame
    """

    def __init__(self, output_dir: sp.Directory, *, filters: FilterData = None):
        super().__init__(output_dir, filters=None)
        self.filter_data: FilterData = filters
        self.name_inner_data: NameFinderInnerData = NameFinderInnerData(self.output_dir, filters=self.filter_data)

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
            Mover arquivos conforme as ocorrências de texto encontradas na tabela/DataFrame df.
        o nome do novo arquivo será igual à ocorrência de texto da coluna 'col_find', podendo
        estender o nome com elementos de outras colunas, tais colunas podem ser informadas (opcionalmente)
        no parâmetro cols_in_name.
            Ex:
        Suponha que a tabela para renomear aquivos tenha a seguinte estrutura:

        A      B        C
        maça   Cidade 1 xxyyy
        banana Cidade 2 yyxxx
        mamão  Cidade 3 xyxyx

        Se passarmos os parâmetros col_find='A' e col_new_name='A' e o texto banana for
        encontrado no(s) documento, o novo nome do arquivo será banana. Caso incluir o parâmetro
        cols_in_name=['B'] o novo nome do arquivo será banana-Cidade 2 ou
        banana-Cidade 2-yyxxx (se incluir cols_in_name=['B', 'C']).

        """
        values: list[TableDocuments] = create_tb_from_names(files)
        for current_tb in values:
            mv_items = self.name_inner_data.get_new_name(
                GenericDocument(current_tb, filters=None)
            )
            move_path_files(mv_items, replace=False)
