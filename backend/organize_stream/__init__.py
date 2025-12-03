#!/usr/bin/env python3

__version__ = '2.4.8'
from .utils import fmt_str_file, remove_bad_chars, clean_string, BAD_STRING_CHARS
from .type_utils import (
    DigitalizedDocument, FilterText, FilterData, EnumDigitalDoc, Observer, NotifyProvider,
    DictKeyWordFiles, DiskFile, DictFileInfo, DictOriginInfo, DictOutputInfo
)
from .read import (
    read_image, read_document, create_tb_from_names
)
from .find import (
    SearchableText, FindNameInnerText, FindNameInnerData, NameFinder,
)
from .text_extract import DocumentTextExtract
from .document import (
    ExtractNameInnerData, ExtractNameInnerText, CreateFileNames
)
from .cartas import CartaCalculo, GenericDocument



