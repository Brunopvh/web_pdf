
from organize_stream import *
from soup_files import *

ORIG = Directory('/home/brunoc/Downloads/Banco de Imagens e PDFs 2025/Original')
DEST = Directory('/home/brunoc/Downloads/SAIDA')
out_zip = DEST.join_file('final.zip')
input_files = InputFiles(ORIG)

images = input_files.images

create = CreateNewFile(lib_digitalized=LibDigitalized.EPI)
extract = DocumentTextExtract()

total = len(images)
for n, pdf in enumerate(images):
    print(f'{n}/{total}')

    info = DiskOriginInfo()
    info.set_file_bytes(pdf.path.read_bytes())
    info.set_extension('.png')
    info.set_filename(pdf.basename())
    create.add_disk_file(info)

final_bytes = create.export_keys_to_zip()

if final_bytes is not None:
    final_bytes.seek(0)
    with open(out_zip.absolute(), 'wb') as f:
        f.write(final_bytes.getvalue())


