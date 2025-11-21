from soup_files import File
from ocr_stream import RecognizeImage as LeitorOcr
from convert_stream import ImageObject as LeitorImagem

leitor_imagem = LeitorImagem(File('/home/brunoc/Documentos/ADS/Fotos/Ficha Bota 42.png'))
ocr = LeitorOcr()
texto = ocr.image_recognize(leitor_imagem)
texto.to_dataframe().to_excel(File('/home/brunoc/Documentos/ADS/Fotos/Ficha Bota 42.xlsx').absolute(), index=False)


