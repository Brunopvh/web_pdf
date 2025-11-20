from __future__ import annotations
import soup_files as sp
from organize_stream import fmt_str_file
from organize_stream.type_utils import DigitalizedDocument, FilterText
from organize_stream.utils import remove_bad_chars
from sheet_stream import (
    ArrayString, ListColumnBody, TableDocuments,
    BAD_STRING_CHARS, ListString, ColumnsTable, ConvertStringDate, LibDate
)
import pandas as pd


class CartaCalculo(DigitalizedDocument):

    default_filter = FilterText(
            'TOI',
            separator=' ',
            key_words=['UC', 'TOI', 'POSTAGEM', 'LIVRO'],
            iqual=False,
            case=False,
        )

    def __init__(self, tb: TableDocuments, *, filters: FilterText):
        super().__init__(tb, filters=filters)

        self.localidades: dict[str, str] = {
            'NOVA MA': 'NOVA MAMORE',
            'MAMORE': 'NOVA MAMORE',
            'GUAJAR': 'GUAJARA MIRIM',
            'GUAJ': 'GUAJARA MIRIM',
            'VISTA': 'VISTA ALEGRE',
            'EXTREM': 'EXTREMA',
        }

    @classmethod
    def create(cls, tb: TableDocuments) -> CartaCalculo:
        return cls(tb, filters=cls.default_filter)

    @property
    def cidade(self) -> str | None:
        lines: ListColumnBody = self.lines
        _loc = None
        for k in self.localidades.keys():
            out = lines.find_text(k)
            if out is not None:
                _loc = self.localidades[k]
                break
        if _loc is None:
            if lines.contains('LOCA'):
                arr = ArrayString([])
                for line in lines:
                    if ' ' in line:
                        arr.extend(line.split(' '))
                    else:
                        arr.add_item(line)
                _loc = arr.get_next_all('LOCA')
                _loc = ' '.join(_loc)
                if len(_loc) > 10:
                    _loc = _loc[:10]

        if _loc is None:
            return None
        return remove_bad_chars(_loc).upper()

    @property
    def medidor(self) -> str | None:
        _medidor = self.lines.find_text('MEDI')

        if _medidor is None:
            return None
        arr = ArrayString(_medidor.split(' '))
        arr = arr.get_next_all('MEDI')
        if arr.is_empty:
            return None
        final_medidor = ' '.join(arr)
        if len(final_medidor) > 12:
            final_medidor = final_medidor[:12]
        return remove_bad_chars(final_medidor)

    def get_line_key(self) -> str | None:
        _check = ['UC', 'TOI', 'TOL']
        _key_word = 'CAR'
        lines = self.lines
        filter_list = ArrayString([])
        elements = ArrayString([])
        list_index: list[int] = []

        # Filtrar os indices desejados.
        for txt in _check:
            idx = lines.find_index(txt)
            if idx is not None:
                if not idx in list_index:
                    list_index.append(idx)

        # Gerar nova lista com os valores filtrados.
        for num in list_index:
            if ' ' in lines[num]:
                filter_list.extend(lines[num].split(' '))
            else:
                filter_list.append(lines[num])

        # Gerar a linha final
        for item in _check:
            i = filter_list.get_next_string(item)
            if i is not None:
                elements.append(i)

        if elements.length == 0:
            final_line: str = ''
        else:
            final_line: str = ' '.join(elements)

        # Incluir a cidade
        cidade = self.cidade
        medidor = self.medidor
        if medidor is not None:
            final_line = f'{final_line}-{medidor}'
        if cidade is not None:
            final_line = f'{final_line}-{cidade}'
        return remove_bad_chars(final_line)

    def get_lines_keys(self) -> ArrayString:
        lines = self.lines
        content: ArrayString = ArrayString([])
        for k in self.uniq_key_words:
            values = lines.find_text(k)
            if values is not None:
                elements = ArrayString(values.split(' '))
                uniq_value = elements.get_next_string(k)
                if uniq_value is not None:
                    content.append(f'{remove_bad_chars(uniq_value)}')
        content.append(self.cidade)
        content.append(self.medidor)
        return content

    def get_output_name_str(self) -> str | None:
        line_key = self.get_line_key()
        if (line_key is None) or (line_key == ''):
            return None
        line_key = fmt_str_file(line_key)
        return line_key


class GenericDocument(DigitalizedDocument):

    def __init__(self, tb: TableDocuments, *, filters: FilterText):
        super().__init__(tb, filters=filters)

    def _get_value_with_str(self, tb: TableDocuments) -> str | None:
        list_new_names: ListString = ListString([])
        tb_txt_file: pd.DataFrame = pd.DataFrame.from_dict(tb)
        df = tb_txt_file[[ColumnsTable.TEXT, ColumnsTable.FILE_PATH]].astype('str')

        # Divide padrões múltiplos separados por "|"
        patterns = [p.strip() for p in self.filters.find_txt.split('|') if p.strip()]
        if not patterns:
            print(f'{__class__.__name__}: Nenhum padrão de busca válido informado.')
            return None

        # Define padrão regex dependendo de "iqual"
        if self.filters.iqual:
            # AQUI estava: '^(' + '|'.join(patterns) + ')$'
            regex_pattern = '^(?:' + '|'.join(patterns) + ')$'  # Mude para (?:...)
        else:
            # AQUI estava: '(' + '|'.join(patterns) + ')'
            regex_pattern = '(?:' + '|'.join(patterns) + ')'  # Mude para (?:...)

        # Filtra linhas no DataFrame
        mask: pd.Series = df[ColumnsTable.TEXT].str.contains(
            regex_pattern,
            case=self.filters.case,
            regex=True,
            na=False
        )
        matched_df = df[mask]
        total_matches = len(matched_df)

        if total_matches == 0:
            return None

        # Para cada linha encontrada, gera nome limpo e adiciona à lista de movimentação
        for _, row in matched_df.iterrows():
            current_line: str = row[ColumnsTable.TEXT]
            if self.uniq_key_words.length > 0:
                for i in self.uniq_key_words:
                    if not i.upper() in current_line.upper():
                        continue
            # Usa o texto da linha como base do novo nome
            current_output_name: str = fmt_str_file(current_line.strip())
            if len(current_output_name) < 4:
                continue
            # Garante que o nome não fique vazio
            if not current_output_name:
                continue
            list_new_names.append(current_output_name)

        if list_new_names.length == 0:
            return None

        output_name: str = ' '.join(list_new_names)
        if len(output_name) < 4:
            return None
        return output_name

    def get_line_key(self) -> str:
        pass

    def get_output_name_str(self) -> str | None:
        if self.tb.get_column(ColumnsTable.TEXT).length == 0:
            return None
        _filename = self._get_value_with_str(self.tb)
        return _filename


class FichaEpi(GenericDocument):

    def __init__(self, tb: TableDocuments, *, filters: FilterText):
        super().__init__(tb, filters=filters)
        self.dias = [
            'segunda-feira', 'terca-feira', 'quarta-feira', 'quinta-feira',
            'sexta-feira', 'sabado',
        ]

    @classmethod
    def create(cls, tb: TableDocuments) -> FichaEpi:
        fil = FilterText('MATR', key_words=['NOME'])
        return cls(tb, filters=fil)

    def get_line_key(self) -> str:
        return self.get_nome()

    def get_output_name_with_extension(self) -> str | None:
        line_date = self.get_date_doc()
        filename = self.get_nome()
        _extension = self.extension_file
        if filename is None:
            return None
        if _extension is None:
            return None
        if line_date is not None:
            filename = f'{filename}-{line_date}'
        filename = fmt_str_file(filename)
        return f'{filename}{_extension}'

    def get_output_name_str(self) -> str | None:
        line_date = self.get_date_doc()
        filename = self.get_nome()

        if filename is None:
            return None
        if line_date is not None:
            filename = f'{filename}-{line_date}'
        return fmt_str_file(filename)

    def get_nome(self) -> str | None:
        return self.tb.get_column(ColumnsTable.TEXT).get_next_string('MATR')

    def get_date_doc(self) -> str | None:
        lines = self.lines
        _date_line: str = None
        _date_txt: str = None
        for d in self.dias:
            txt = lines.find_text(d)
            if txt is not None:
                _date_line = txt
                _date_txt = d
                break
        if _date_line is None:
            return None
        idx = _date_line.find(_date_txt)
        _date_line = _date_line[idx:].replace(_date_txt, '').strip()
        try:
            arr = ArrayString(_date_line.split(' '))
            conv: dict = ConvertStringDate().month_to_number
            _day = arr.get_back_string('de')
            _year = arr[-1]
            _month = arr.get_next_string('de').strip().lower()
            _month = conv[_month]
        except Exception as e:
            pass
        else:
            _date_line = f'{_year}-{_month}-{_day}'.replace('.', '')
        return _date_line
