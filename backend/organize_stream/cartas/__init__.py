from .carta_calculo import (
    CartaCalculo, GenericDocument, DigitalizedDocument, FichaEpi
)
from organize_stream.utils import fmt_str_file
import soup_files as sp
import shutil


def move_cartas(cartas: list[DigitalizedDocument], output_dir: sp.Directory):
    output_dir.mkdir()
    for carta in cartas:
        try:
            src_file: sp.File = carta.file_path_origin
            if src_file is None:
                continue
            if not src_file.exists():
                continue
            output_file_name = fmt_str_file(carta.get_line_key())

            if output_file_name is None:
                continue
            if carta.extension_file is None:
                continue
            output_file_name = f'{output_file_name}{carta.extension_file}'
        except Exception as err:
            print(err)
        else:
            dest_file = output_dir.join_file(output_file_name)
            if not isinstance(dest_file, sp.File):
                continue
            if dest_file.exists():
                continue
            try:
                print(f'Movendo: {dest_file.absolute()}')
                shutil.move(src_file.absolute(), dest_file.absolute())
            except Exception as e:
                print(e)


__all__ = [
    'CartaCalculo', 'GenericDocument', 'move_cartas', 'FichaEpi'
]
