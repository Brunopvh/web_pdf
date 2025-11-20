#!/usr/bin/env python3

__version__ = '2.4.7'
from .utils import fmt_str_file, remove_bad_chars, clean_string, BAD_STRING_CHARS
from .type_utils import (
    DigitalizedDocument, FilterText, FilterData, LibDigitalized, Observer, NotifyProvider,
    KeyWordsFileName, DiskFile, DiskFileInfo, DiskOriginInfo, DiskOutputInfo
)
from .read import (
    read_image, read_document, create_tb_from_names
)
from .find import (
    SearchableText, NameFinderInnerText, NameFinderInnerData, NameFinder,
    OriginFileName, DestFilePath
)
from .text_extract import DocumentTextExtract
from .document import (
    ExtractNameInnerData, ExtractNameInnerText, CreateNewFile
)
from .cartas import CartaCalculo, GenericDocument



