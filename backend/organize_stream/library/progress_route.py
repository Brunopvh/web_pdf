from fastapi import APIRouter
from fastapi.responses import JSONResponse
from typing import Any
from io import BytesIO
import tempfile
import pandas as pd
import convert_stream as cs
import zipfile
import os
import soup_files as sp
from organize_stream.document import CreateFileNames, ExtractNameInnerData
from organize_stream.type_utils import (
    FilterData, FilterText, EnumDigitalDoc, DictOriginInfo, DictOutputInfo
)
from organize_stream.text_extract import DocumentTextExtract
from sheet_stream import ListItems, TableDocuments, ColumnsTable, ListColumnBody

# Define o roteador para as rotas de progresso
router = APIRouter()
TASK_PROGRESS_STATE: dict[str, dict[str, Any]] = {}


def create_progress_with_id(task_id: str) -> dict[str, Any]:
    """
        Cria um progresso vazio e adiciona no dicionário global.
        
    TASK_PROGRESS_STATE
    """
    new_state = {
        "current": 0,
        "total": 0,
        "done": False,
        "zip_path": None,
        "task_id": task_id,
        "message": "Aguarde!",
    }
    TASK_PROGRESS_STATE[task_id] = new_state
    return new_state


def get_id_progress_state(task_id: str) -> dict[str, Any] | None:
    """
        Obtém o estado de progresso para um ID de tarefa específico.
    """
    try:
        return TASK_PROGRESS_STATE.get(task_id)
    except Exception as e:
        print(e)
        return None


# =============== ROTA PROGRESSO ==================
@router.get("/progress/{task_id}")
async def get_json_progress(task_id: str) -> JSONResponse:
    """
        Retorna o status do processamento para o frontend.
    """
    # Obtém o estado usando o ID da tarefa na URL
    current_progress = get_id_progress_state(task_id)
    if current_progress is None:
        return JSONResponse({
        "current": 0,
        "total": 0,
        "progress": 0,
        "done": False,
        "task_id": task_id,
    })
        
    if current_progress["total"]:
        pbar = ((current_progress["current"] + 1) / current_progress["total"]) * 100
    else:
        pbar = 0
    return JSONResponse({
        "current": current_progress["current"],
        "total": current_progress["total"],
        "progress": pbar,
        "done": current_progress["done"],
        "task_id": task_id,
    })


def thread_images_to_pdfs(images: list[str], task_id: str) -> None:
    """
    Recebe uma lista de imagens e junta tudo em arquivos pdf, o download final
    são arquivos .pdf dentro de um .zip
    """
    # Criar diretório temporário para saída
    temp_dir = tempfile.mkdtemp()
    _output_zip = os.path.join(temp_dir, "resultado.zip")
    pdf_stream = cs.PdfStream()
    current_progress: dict[str, Any] = get_id_progress_state(task_id)

    try:
        current_progress['total'] = len(images)
        with zipfile.ZipFile(_output_zip, "w") as zipf:
            for idx, path in enumerate(images):
                current_progress["current"] = idx
                with open(path, "rb") as fp:
                    raw_bytes = fp.read()
                im = cs.ImageObject.create_from_bytes(raw_bytes)
                pdf_stream.add_image(im)
                doc = pdf_stream.to_document()
                pdf_bytes: BytesIO = doc.to_bytes()
                filename = f"documento_{idx}.pdf"
                zipf.writestr(filename, pdf_bytes.getvalue())
                pdf_stream.clear()
                del doc
        # finalizou
        current_progress.update({"done": True, "zip_path": _output_zip})
    except Exception as e:
        current_progress.update({"done": True, "zip_path": None})
        print(f"[ERRO] Worker falhou: {e}")


def thread_docs_to_sheet(**kwargs) -> None:
    """
        Recebe um dicionário com chaves que apontam para 
    lista de pdfs e imagens, extrai os textos e converte em planilha excel.
    """
    current_progress: dict[str, Any] = get_id_progress_state(kwargs.get("task_id"))
    files_dict: ListItems[DictOriginInfo] = kwargs.get("documents")
    values_documents: ListItems[pd.DataFrame] = ListItems()    
    current_progress['total'] = len(files_dict)
    extractor = DocumentTextExtract()
    extractor.notify_observers = False
    
    try:
        image: DictOriginInfo
        for n, image in enumerate(files_dict):
            current_progress["current"] = n
            tb: TableDocuments
            if image.get_extension() in sp.LibraryDocs.IMAGE.value:
                tb = extractor.read_image(image.get_file_bytes())
            elif image.get_extension() in sp.LibraryDocs.PDF.value:
                tb = extractor.read_document(image.get_file_bytes())
            else:
                continue
            
            if tb is None:
                continue
            if tb.length == 0:
                continue
            num = tb.get_column(ColumnsTable.TEXT.value).length
            tb.set_column(ListColumnBody(ColumnsTable.FILETYPE, [image.get_extension()] * num))
            tb.set_column(ListColumnBody(ColumnsTable.FILE_NAME, [image.get_name()] * num))
            values_documents.append(tb.to_data())
            
    except Exception as e:
        current_progress.update({"done": True, "zip_path": None})
        print(f"[ERRO] Falha ao tentar extrair texto dos documentos: {e}")
        return
    else:
        if values_documents.length == 0:
            current_progress.update({"done": True, "zip_path": None})
            print(f"[ERRO] Falha ao tentar extrair texto dos documentos")
            return

    temp_dir: sp.Directory = sp.Directory(tempfile.mkdtemp())
    temp_dir.mkdir()
    _output_zip: sp.File = temp_dir.join_file("documentos.zip")
    try:
        buff_excel: BytesIO = BytesIO()
        df = pd.concat(values_documents)
        df = df[[ColumnsTable.FILETYPE, ColumnsTable.FILE_NAME, ColumnsTable.TEXT,]]
        df.to_excel(buff_excel, index=False)
        buff_excel.seek(0)
        
        # Salvar em zip
        buff_zip = BytesIO()
        with zipfile.ZipFile(buff_zip, "w") as zipf:
            zipf.writestr('documentos.xlsx', buff_excel.getvalue())
            
        # Salvar o zip em disco para download
        buff_zip.seek(0)
        _output_zip.path.write_bytes(buff_zip.getvalue())
        # finalizou
        current_progress.update({"done": True, "zip_path": _output_zip.absolute()})
    except Exception as e:
        current_progress.update({"done": True, "zip_path": None})
        print(f"[ERRO] Falha ao tentar baixar o arquivo .zip: {e}")
        
    
def thread_organize_documents(**kwargs: dict[str, Any]) -> None:
    """
    Recebe uma lista de imagens e junta tudo em arquivos pdf, o download final
    são arquivos .pdf dentro de um .zip
    """
    # Criar diretório temporário para saída
    temp_dir: sp.Directory = sp.Directory(tempfile.mkdtemp())
    temp_dir.mkdir()
    _output_zip: str = temp_dir.join_file("resultado.zip").absolute()
    current_progress: dict[str, Any] = get_id_progress_state(kwargs['task_id'])
    current_progress['total'] = len(kwargs['images']) + len(kwargs['pdfs'])
    current_progress['current'] = 0
    
    name_finder: CreateFileNames
    if kwargs['digitalized_type'] == 'EPIS':
        name_finder = CreateFileNames(lib_digitalized=EnumDigitalDoc.EPI)
    elif kwargs['digitalized_type'] == 'CARTAS':
        name_finder = CreateFileNames(lib_digitalized=EnumDigitalDoc.CARTA_CALCULO)
    else:
        if kwargs['pattern'] is None:
            current_progress.update({"done": True, "zip_path": None})
            print(f"DEBUG: thread_organize_documents falhou, o filtro de texto é nulo!")
            return
        filter_text = FilterText(kwargs['pattern'])
        name_finder = CreateFileNames(filters=filter_text)
           
    final_bytes: BytesIO | None
    try:
        count = 0
        documents: ListItems[DictOriginInfo] = kwargs['pdfs']
        total = len(documents)
        for num, file_info in enumerate(documents):
            current_progress["current"] = count
            count += 1
            print(f'{num+1}/{total}')
            name_finder.add_disk_file(file_info) 
            
        final_bytes: BytesIO | None = name_finder.export_new_files_to_zip()
        if final_bytes is None:
            current_progress.update({"done": True, "zip_path": None})
            print(f"DEBUG: thread_organize_documents falhou, o arquivo zip é nulo!")
            return
    except Exception as e:
        current_progress.update({"done": True, "zip_path": None})
        print(f"\n[ERRO] thread_organize_documents falhou ao tentar gerar o arquivo ZIP: {e}")
    else:
        try:
            path_excel = temp_dir.join_file('dados.xlsx')
            name_finder.export_log_actions().to_excel(path_excel.absolute(), index=False)
            final_bytes.seek(0)
            with zipfile.ZipFile(final_bytes, 'a', zipfile.ZIP_DEFLATED) as zipf:
                # writestr adiciona bytes na memória.
                zipf.writestr('dados.xlsx', path_excel.path.read_bytes())
            final_bytes.seek(0)
            with open(_output_zip, 'wb') as fp:
                fp.write(final_bytes.getvalue())
            
        except Exception as e:
            current_progress.update({"done": True, "zip_path": None})
            print(f"\n[ERRO] thread_organize_documents falhou ao tentar salvar o arquivo ZIP: {e}")
        else:
            current_progress.update({"done": True, "zip_path": _output_zip})
            
            
  
def thread_organize_documents_with_sheet(**kwargs: dict[str, Any]) -> None:
    """
    Recebe um dicionario com as chaves
    
    df: pd.Dataframe: aponta para um dataframe com dados base para o filtro de dados
    col_find: str: coluna onde o texto deve ser filtrado
    col_new_name: str: coluna que aponta para o novo nome de arquivo.
    files: list[File]: aponta para uma lista de arquivos.
    task_id: str: id do processo.
    output_dir: Directory: diretório destino dos arquivos.
    """
    # Diretório temporário para saída de dados.
    temp_dir: sp.Directory = kwargs["output_dir"]
    temp_dir.mkdir()
    list_documents_files: list[sp.File] = kwargs["files"]
    _output_zip: str = temp_dir.join_file("resultado.zip").absolute()
    progress_data: dict[str, Any] = get_id_progress_state(kwargs['task_id'])
    progress_data['total'] = len(list_documents_files)
    progress_data['current'] = 0
    find_name_inner_data: ExtractNameInnerData
    
    # Renomear os arquivos
    try:
        filter_data = FilterData(
            kwargs["df"], col_find=kwargs["col_find"], col_new_name=kwargs["col_new_name"], cols_in_name=[]
        )
        find_name_inner_data: ExtractNameInnerData = ExtractNameInnerData(temp_dir, filters=filter_data)
        find_name_inner_data.save_tables = False
        find_name_inner_data.extractor.notify_observers = False
        
        for num_prog, file_doc in enumerate(list_documents_files):
            progress_data['current'] = num_prog + 1
            if file_doc.is_image():
                tb_img = find_name_inner_data.extractor.read_image(file_doc)
                if (tb_img is not None) and (tb_img.length > 0):
                    find_name_inner_data.add_table(tb_img)
            elif file_doc.is_pdf():
                tb_pdf = find_name_inner_data.extractor.read_document(file_doc)
                if (tb_pdf is not None) and (tb_pdf.length > 0):
                    find_name_inner_data.add_table(tb_pdf)
                    
        find_name_inner_data.export_final_table()      
        # Gerar uma lista de arquivos
        input_files = sp.InputFiles(temp_dir)
        final_files: list[sp.File] = input_files.pdfs
        final_files.extend(input_files.images)
        final_files.extend(input_files.sheets)
        
        #zip_buffer = BytesIO()
        with zipfile.ZipFile(_output_zip, "w") as zipf:
            for doc_file in final_files:
                _doc_bytes: bytes = doc_file.path.read_bytes()
                zipf.writestr(doc_file.basename(), _doc_bytes)
        #zip_buffer.seek(0)
    except Exception as e:
        progress_data.update({"done": True, "zip_path": None})
        print(f"\n[ERRO] Falha ao tentar gerar o arquivo ZIP: {e}")
    else:
        progress_data.update({"done": True, "zip_path": _output_zip})
    
        