#!/usr/bin/env python3
#
"""
Objetivos desse módulo:
    - Objetivo geral:
        Organizar arquivos PDFs e Imagens com base em padrões de texto presentes nesses arquivos

    - Objetivos específicos:
        - Converter ter texto/‘string’ ou lista de ‘strings’ em tabelas (do tipo DataFrame ou dicionário).
        - Ser capaz de filtrar por textos e padrões de textos nas imagens/pdfs.
        - Renomear os arquivos/documentos com base em padrões de texto informado ou usando planilha como
        fonte de dados.
        - Mostrar ‘logs’ ou algo parecido(csv, xlsx, json), para informar os arquivos renomeados com sucesso e os
        que apresentaram erros.
        - Listar arquivos que contém um texto filtrado.
"""
from __future__ import annotations
import os
import sys

main_file = os.path.realpath(__file__)
dir_of_project = os.path.dirname(main_file)
dir_root = os.path.dirname(dir_of_project)
sys.path.insert(0, dir_root)


from organize_stream import __version__


def test():
    print(f'organize V{__version__}')


def main():
    test()


if __name__ == '__main__':
    main()
