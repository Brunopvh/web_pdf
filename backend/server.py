#!/usr/bin/env python3
"""
    
"""
from __future__ import annotations
import os
from fastapi import FastAPI, UploadFile, File
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi import UploadFile, File
from fastapi.responses import JSONResponse
from fastapi import Form
import base64
from typing import Any
import io
import zipfile
import convert_stream as cs
import ocr_stream as ocr
import soup_files as sp
import pandas as pd
import tempfile
import threading
from organize_stream import (
    FilterText, FilterData, LibDigitalized
)
from organize_stream.document.name_files import (
    NameFileInnerTable, ExtractNameInnerData, ExtractNameInnerText
)
from sheet_stream import ReadFileSheet, LibSheet
#from fastapi.responses import StreamingResponse, JSONResponse

SERVER_FILE = os.path.abspath(os.path.realpath(__file__))
DIR_ROOT = os.path.abspath(os.path.join(os.path.dirname(SERVER_FILE), '..'))
DIR_ASSETS = os.path.join(DIR_ROOT, 'frontend', 'assets', 'data')
FILE_CONF = os.path.join(DIR_ASSETS, 'ips.json')
TESS_FILE = '/usr/bin/tesseract'

app = FastAPI()

# Habilitar CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def get_temp_dir():
    # Criar diretório temporário para saída
    temp_dir = tempfile.mkdtemp()
    return temp_dir


# ===================== OBTER ROTAS E IPS DO ARQUIVO JSON ====
def get_json_info(file_json: str = FILE_CONF) -> dict[str, Any] | None:
    """
        Ler o arquivo .json para obter informações de rotas e IPS.
    """
    try:
        data = sp.JsonConvert.from_file(sp.File(file_json)).to_json_data()
        return data.to_dict()
    except Exception as err:
        print(err)
    return None


route_info = get_json_info()
print(route_info)


def create_progress() -> dict[str, Any]:
    return {
        "current": 0,
        "total": 0,
        "done": False,
        "zip_path": None,
    }


# Estado global simples
progress_data: dict[str, Any] = create_progress()

# =============== ROTA PROGRESSO ==================
@app.get("/progress")
async def get_progress():
    if progress_data["total"]:
        pbar = ((progress_data["current"] + 1) / progress_data["total"]) * 100
    else:
        pbar = 0
    return JSONResponse({
        "current": progress_data["current"],
        "total": progress_data["total"],
        "progress": pbar,
        "done": progress_data["done"],
    })


# =============== WORKER ==================
def worker_progress(files: list[str]):
    # Criar diretório temporário para saída
    temp_dir = tempfile.mkdtemp()
    _output_zip = os.path.join(temp_dir, "resultado.zip")
    pdf_stream = cs.PdfStream()

    try:
        progress_data['total'] = len(files)
        with zipfile.ZipFile(_output_zip, "w") as zipf:
            for idx, path in enumerate(files):
                progress_data["current"] = idx
                with open(path, "rb") as fp:
                    raw_bytes = fp.read()
                im = cs.ImageObject.create_from_bytes(raw_bytes)
                pdf_stream.add_image(im)
                doc = pdf_stream.to_document()
                pdf_bytes: io.BytesIO = doc.to_bytes()
                filename = f"documento_{idx}.pdf"
                zipf.writestr(filename, pdf_bytes.getvalue())
                pdf_stream.clear()
                del doc
        # finalizou
        progress_data.update({"done": True, "zip_path": _output_zip})

    except Exception as e:
        progress_data.update({"done": True, "zip_path": None})
        print(f"[ERRO] Worker falhou: {e}")


# =================== ROTA PARA OCR EM IMAGENS =====================

@app.post(f"/{route_info['rt_ocr']}")
async def ocr_images(
            files: list[UploadFile] = File(...),
        ):
    """
        Aplica OCR em imagens enviadas e retorna um ZIP com os PDFs resultantes.
    """
    zip_buffer = io.BytesIO()
    recognize_img = ocr.RecognizeImage(
        ocr.BinTesseract(File(TESS_FILE))
    )
    with zipfile.ZipFile(zip_buffer, "w") as zipf:
        for i, file in enumerate(files):
            content = await file.read()
            image = cs.ImageObject.create_from_bytes(content)
            doc_pdf = recognize_img.image_recognize(image).to_document()
            zipf.writestr(f"ocr_documento_{i + 1}.pdf", doc_pdf.to_bytes().getvalue())
            del doc_pdf
    zip_buffer.seek(0)

    return StreamingResponse(
        zip_buffer,
        media_type="application/zip",
        headers={"Content-Disposition": "attachment; filename=ocr_documents.zip"},
    )


# ===================== ROTA PDF PARA IMAGENS =====================
@app.post(f"/{route_info['rt_convert_pdf']}")
async def convert_pdfs(files: list[UploadFile] = File(...)):
    """
        Rota para converter PDFs em imagens
    """
    final_list_imgs: list[cs.ImageObject] = []
    for file in files:
        file_bytes = await file.read()
        tmp_doc = cs.DocumentPdf(io.BytesIO(file_bytes))
        conv_pdf_to_images = cs.ConvertPdfToImages.create(tmp_doc)
        current_imgs: list[cs.ImageObject] = conv_pdf_to_images.to_images()
        final_list_imgs.extend(current_imgs)
        current_imgs.clear()
        del tmp_doc
        del conv_pdf_to_images
    
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w") as zipf:
        # Compactar as imagens da lista em formato zip.
        for n, img in enumerate(final_list_imgs):
            _bytes_img: bytes = img.to_bytes().getvalue()
            zipf.writestr(f"imagem_{n + 1}.png", _bytes_img)
            del _bytes_img 
    final_list_imgs.clear()
    del final_list_imgs
    zip_buffer.seek(0)
    return StreamingResponse(
        zip_buffer,
        media_type="application/zip",
        headers={"Content-Disposition": "attachment; filename=pdf-para-imagens.zip"},
    )


# ===================== ROTA DIVIDIR PDF =====================
@app.post(f"/{route_info['rt_split_pdf']}")
async def split_pdf(files: list[UploadFile] = File(...)):
    """
        Recebe uma lista de arquivos PDFs, converte cada página de cada
    PDF será convertida em arquivo PDF individual.
    """
    pages: list[cs.PageDocumentPdf] = []
    for file_pdf in files:
        current_bytes = await file_pdf.read()
        doc = cs.DocumentPdf(io.BytesIO(current_bytes))
        pages.extend(doc.to_pages())
        del doc

    # Criar um ZIP em memória
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w") as zipf:
        for i, page in enumerate(pages):
            current_doc = cs.DocumentPdf.create_from_pages([page])
            current_bytes = current_doc.to_bytes()
            zipf.writestr(f"pag_{i + 1}.pdf", current_bytes.getvalue())
            del current_doc
            del current_bytes

    zip_buffer.seek(0)
    return StreamingResponse(
        zip_buffer,
        media_type="application/zip",
        headers={"Content-Disposition": "attachment; filename=paginas_divididas.zip"},
    )


@app.post(f"/{route_info['rt_join_pdf']}")
async def join_pdfs(files: list[UploadFile] = File(...)):
    """
        Recebe uma lista de arquivos PDF e junta tudo em arquivo único.
    """
    # Nome do arquivo a ser baixado.
    output_filename = 'Documento-juntado.pdf'
    collection_pages: cs.CollectionPagePdf = cs.CollectionPagePdf([])

    for file in files:
        pdf_bytes: bytes = await file.read()
        _doc = cs.DocumentPdf(io.BytesIO(pdf_bytes))
        collection_pages.add_pages(_doc.to_pages())
        del _doc
    new_doc = cs.DocumentPdf.create_from_pages(collection_pages)
    # Retornar como resposta HTTP
    return StreamingResponse(
        new_doc.to_bytes(),
        media_type="application/pdf",
        headers={"Content-Disposition": "attachment; filename={}".format(output_filename)}
    )


# =============== ROTA PROCESSAR IMAGENS ==================
@app.post(f"/{route_info['rt_imgs_to_pdf']}")
async def process_images(files: list[UploadFile] = File(...)):
    image_files: list[str] = []

    # Salvar os uploads em arquivos temporários
    for upload in files:
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".jpg")
        content: bytes = await upload.read()
        temp_file.write(content)
        temp_file.close()
        image_files.append(temp_file.name)
    # Rodar conversão em thread
    thread = threading.Thread(target=worker_progress, args=(image_files,))
    thread.start()
    return {"message": "Processamento iniciado"}


# =============== ROTA DOWNLOAD ==================
@app.get("/download")
async def download_result():
    if (not progress_data["done"]) or (not progress_data["zip_path"]):
        return JSONResponse({"error": "Arquivo ainda não está pronto"}, status_code=400)

    print(f'Baixando: {progress_data["zip_path"]}')
    zip_path = progress_data["zip_path"]
    return StreamingResponse(
        open(zip_path, "rb"),
        media_type="application/zip",
        headers={"Content-Disposition": "attachment; filename=result.zip"},
    )


# ===================== ROTA UNIFICADA PROCESSAR DOCUMENTOS =====================

@app.post(f"/{route_info['rt_process_docs']}")
async def organize_documents_with_sheet(
            pdfs: list[UploadFile] = File(default=[]),
            images: list[UploadFile] = File(default=[]),
            file_sheet: UploadFile = File(default=None),
            column_name: str = Form(default=None),  # NOVO
        ):
    """
    Rota unificada para processar PDFs, imagens e renomear com base em uma planilha Excel.
    """

    temp_dir: str = tempfile.mkdtemp()
    progress_data.update({"current": 0, "total": 0, "done": False, "zip_path": None})
    list_files: list[UploadFile] = []
    list_files.extend(pdfs)
    list_files.extend(images)
    sheet_bytes: bytes = await file_sheet.read()
    src_df: pd.DataFrame = ReadFileSheet(io.BytesIO(sheet_bytes), lib_sheet=LibSheet.EXCEL).get_dataframe()
    try:
        # Salvar todos os arquivos recebidos
        saved_files: list[str] = []
        for current_file in list_files:
            if current_file is None:
                continue
            content: bytes = await current_file.read()
            file_path = os.path.join(temp_dir, current_file.filename)
            with open(file_path, "wb") as f:
                f.write(content)
            saved_files.append(file_path)
        total_files = len(saved_files)
        progress_data["total"] = total_files
        
        src_dir: sp.Directory = sp.Directory(temp_dir)
        input_files = sp.InputFiles(src_dir)
        __files_pdf = input_files.pdfs
        __files_images = input_files.images
        filter_data = FilterData(
            src_df, col_find=column_name, col_new_name=column_name, cols_in_name=[]
        )
        name_finder = ExtractNameInnerData(src_dir, filters=filter_data)
        for img in __files_images:
            name_finder.add_table(
                name_finder.extractor.read_image(img)
            )
        for file_pdf in __files_pdf:
            name_finder.add_table(
                name_finder.extractor.read_document(file_pdf)
            )
        progress_data.update({"done": True})
        
        # Gerar uma lista de arquivos PDF
        docs_list: list[sp.File] = input_files.pdfs
        # Gerar uma lista de imagens.
        docs_imgs: list[sp.File] = input_files.images
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, "w") as zipf:
            for file_pdf in docs_list:
                _pdf_bytes: bytes = file_pdf.path.read_bytes()
                zipf.writestr(file_pdf.basename(), _pdf_bytes)
                
            for file_img in docs_imgs:
                _img_bytes: bytes = file_img.path.read_bytes()
                zipf.writestr(file_img.basename(), _img_bytes)
        zip_buffer.seek(0)

        # Retornar o ZIP finalizado
        return StreamingResponse(
            zip_buffer,
            media_type="application/zip",
            headers={"Content-Disposition": "attachment; filename=filtrado_com_tabela.zip"},
        )

    except Exception as e:
        progress_data.update({"done": True, "zip_path": None})
        print(f"[ERRO] Falha ao processar documentos: {e}")
        return JSONResponse({"error": str(e)}, status_code=500)


@app.post(f"/{route_info['rt_process_pattern']}")
async def organize_documents_with_pattern(
            pdfs: list[UploadFile] = File(default=[]),
            images: list[UploadFile] = File(default=[]),
            pattern: str = Form(default=None),  # padrão de texto
        ):
    """
    Rota alternativa usada quando o usuário digita um padrão de texto
    ao invés de enviar planilha XLSX e nome de coluna.
    Retorna um ZIP com os arquivos processados.
    """
    if not pattern:
        e = "O parâmetro 'pattern' é obrigatório nesta rota."
        return JSONResponse({"error": str(e)}, status_code=500)

    #temp_dir: str = tempfile.mkdtemp()
    progress_data.update({"current": 0, "total": 0, "done": False, "zip_path": None})

    # Objeto para organizar os arquivos
    filter_text = FilterText(pattern)
    name_finder = NameFileInnerTable(filters=filter_text)
    total_files = len(pdfs) + len(images)
    # Renomear os arquivos recebidos usando os bytes.

    # Imagens
    # Processar e renomear as imagens.
    image_file: UploadFile
    __status = True
    for image_file in images:
        if image_file is None:
            continue
        image_bytes: bytes = await image_file.read()
        try:
            name_finder.add_image(image_bytes)
        except Exception as e:
            print(f"[ERRO] Falha ao processar imagem: {e}")

    progress_data['current'] = 50
    for file_pdf in pdfs:
        if file_pdf is None:
            continue
        pdf_bytes: bytes = await file_pdf.read()
        try:
            name_finder.add_document(pdf_bytes)
        except Exception as e:
            print(f"[ERRO] Falha ao processar documento: {e}")
    progress_data["total"] = total_files

    #progress_data.update({"done": True, "zip_path": None})
    #print(f"DEBUG: Falha {err}")
    #return JSONResponse({"error": str(err)}, status_code=500)

    # Gravar os dados em bytes ZIP.
    try:
        zip_bytes: io.BytesIO | None = name_finder.export_keys_to_zip()
        zip_bytes.seek(0)
    except Exception as e:
        progress_data.update({"done": True, "zip_path": None})
        print(f"[ERRO] Falha ao processar documentos: {e}")
        return JSONResponse({"error": str(e)}, status_code=500)
    else:
        # Retornar o ZIP para download.
        return StreamingResponse(
            zip_bytes,
            media_type="application/zip",
            headers={"Content-Disposition": "attachment; filename=resultado_final.zip"},
        )


