from .observer import (
    Observer, NotifyProvider, ObserverTableExtraction, NotifyTableExtract
)
from .digital_doc import DigitalizedDocument, FilterText, FilterData
from .keyword_files import (
    DestFilePath, OriginFileName, LibDigitalized, KeyFiles,
    KeyWordsFileName, DiskFile, DynamicFile, DiskOriginInfo, DiskOutputInfo, DiskFileInfo
)
from soup_files import File, ProgressBarAdapter


class TextProgress(object):

    def __init__(self, total: int = 1, start_value: int = 0):
        self.start_value = start_value
        self.total = total
        if total < start_value:
            raise ValueError(f'Total {total} is less than start value {start_value}')
        if total == 0:
            raise ValueError(f'Total {total} is zero')
        self.__default_text: str = 'Progresso'
        self.__pbar: ProgressBarAdapter = ProgressBarAdapter()

    def set_default_text(self, text: str):
        self.__default_text = text

    def set_pbar(self, pbar: ProgressBarAdapter):
        self.__pbar = pbar

    def get_pbar(self) -> ProgressBarAdapter:
        return self.__pbar

    def start_pbar(self):
        self.__pbar.start()

    def stop_pbar(self):
        self.__pbar.stop()

    def set_update(self, text: str = None):
        if text is None:
            self.__pbar.update(
                ((self.start_value+1) / self.total) * 100,
                self.__default_text,
            )
        else:
            self.__pbar.update(
                ((self.start_value + 1) / self.total) * 100,
                f'{text}',
            )
        self.start_value += 1


