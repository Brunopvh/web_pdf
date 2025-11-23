from soup_files import *
from ocr_stream import RecognizeImage as LeitorOcr
from convert_stream import ImageObject as LeitorImagem
from organize_stream import *

src = Directory('/home/brunoc/Downloads/GM E NM/OutputString')
out = Directory('/home/brunoc/Downloads/saida')
output_sheet = out.join_file(f'Teste.xlsx')

files = InputFiles(src).images

name = CreateFileNames(lib_digitalized=EnumDigitalDoc.CARTA_CALCULO)
total = len(files)
for n, file in enumerate(files):
    print(f'{n+1}/{total}: {file.name()}')
    name.rename_image(file, out)
name.export_log_actions().to_excel(output_sheet.absolute())


