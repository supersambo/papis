"""This module implements custom exceptions used to make the code more readable."""

import papis.strings


class DefaultSettingValueMissing(KeyError):
    """Exception raised when a configuration setting is missing and has no
    default value."""

    def __init__(self, key: str) -> None:
        message = """

    The configuration setting '{0}' is not defined.
    Try setting its value in your configuration file as such:

        [settings]
        {0} = some-value

    Don't forget to check the documentation.
        """.format(key)
        super().__init__(message)


class DocumentFolderNotFound(FileNotFoundError):
    """Exception raised when a document has no main folder."""

    def __init__(self, doc: str) -> None:
        super().__init__("{}: '{}'".format(
            papis.strings.no_folder_attached_to_document,
            doc))
