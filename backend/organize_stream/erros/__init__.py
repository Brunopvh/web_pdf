
class TableFileEmptyError(Exception):
    def __init__(self, *args):
        super().__init__(*args)


class InvalidTDigitalizedDocument(Exception):

    def __init__(self, *args):
        super().__init__(*args)


class InvalidSrcFile(Exception):

    def __init__(self, *args):
        super().__init__(*args)


class ExtensionFileEmptyError(Exception):

    def __init__(self, *args):
        super().__init__(*args)


class DiskFileInvalidError(Exception):

    def __init__(self, *args):
        super().__init__(*args)
