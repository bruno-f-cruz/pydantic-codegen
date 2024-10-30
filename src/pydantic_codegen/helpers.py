import datetime
import os
import re
from typing import Any, List, Optional, Union

_SPECIAL_CHARACTERS = r"!@#$%^&*()+=<>?,./;:'\"[]{}|\\`~"
_TRANSLATION_TABLE = str.maketrans("", "", _SPECIAL_CHARACTERS)


def normalize_model_source_provenance(model_source: Any) -> str:
    try:
        return str(model_source)
    except TypeError as e:
        raise TypeError("model_source must be a string or os.PathLike[str]") from e


def is_pascal_case(value: str) -> bool:
    if value.isidentifier():
        return value[1].isupper() if value[0] == "_" else value[0].isupper()
    else:
        return False


def to_pascal_case(value: str) -> str:
    suffix = value[0] if value[0] == "_" else ""  # Honor the first underscore
    return suffix + "".join([word.capitalize() for word in re.split(r"[_\- ]", value)])


def sanitize_class_name(class_name: str) -> str:
    # If the class name starts with a digit, we prefix it with an underscore
    class_name = class_name.translate(_TRANSLATION_TABLE)
    if class_name[0].isdigit():
        class_name = "_" + class_name

    return to_pascal_case(class_name)


def create_enum_key_from_class_name(value: str) -> str:
    suffix = "_" if (value[0] == "_" or value[0].isdigit()) else ""
    return suffix + re.compile(r"[\W_]+").sub("_", value).upper()


def unindent(text: str) -> str:
    first_line = text.split("\n")[0]
    while first_line.strip() == "":
        text = text[1:]
        first_line = text.split("\n")[0]
    indent = len(first_line) - len(first_line.lstrip())
    return "\n".join([line[indent:] for line in text.split("\n")])


def indent_line(text: str, level: int = 0) -> str:
    if level == 0:
        return text
    if level < 0:
        raise ValueError("Level must be greater than 0")
    return "\t" * level + text


def indent_block(text: str, level: int = 0) -> str:
    indented = "".join([indent_line(line, level) + "\n" for line in text.split("\n")])
    return indented[: -(level + 1)]  # Remove the last newline and added tabs and to honor input formatting


def count_indent_level(text: str) -> int:
    return len(text) - len(text.lstrip("\t"))


def replace_tabs_with_spaces(text: str) -> str:
    return text.replace("\t", 4 * " ")


class TemplateHelper:
    def indent(self, text: str, level: int = 0) -> str:
        return indent_block(text, level)

    @staticmethod
    def import_statements() -> str:
        return "from pydantic import Field, RootModel\nfrom typing import Union, Annotated, Literal\n"

    @staticmethod
    def import_statement(module_name: str, class_name: Union[str, List[str]]):
        if isinstance(class_name, list):
            class_name = ", ".join([cls for cls in class_name])
        return "from {module_name} import {class_name}\n".format(module_name=module_name, class_name=class_name)

    @classmethod
    def class_header(cls, class_name: str, parent_name: Optional[Union[str, List[str]]] = None):
        if parent_name is None:
            return cls._orfan_class_header(class_name)
        if isinstance(parent_name, list):
            if len(parent_name) == 0:
                return cls._orfan_class_header(class_name)
            else:
                parent_name = ", ".join([cls for cls in class_name])
        return "\n\nclass {class_name}({parent_name}):\n\n".format(class_name=class_name, parent_name=parent_name)

    @staticmethod
    def _orfan_class_header(class_name: str):
        return "\n\nclass {class_name}:\n\n".format(class_name=class_name)

    @staticmethod
    def literal_field(name: str, value: str):
        return "{field_name}: Literal[{value}] = {value}\n".format(field_name=name, value=value)

    @staticmethod
    def type_all_from_subclasses(parent_name: str):
        return "\nALL = tuple({parent_name}.__subclasses__())\n".format(parent_name=parent_name)

    @staticmethod
    def type_one_of(parent_name: str, discriminator: str):
        return '\n\nclass ONE_OF(RootModel):\n\troot: Annotated[Union[tuple({parent_name}.__subclasses__())], Field(discriminator="{discriminator}")]\n'.format(
            parent_name=parent_name, discriminator=discriminator
        )

    @staticmethod
    def abbreviation_map():
        _s = "\n"
        _s += "abbreviation_map = {m().abbreviation: m() for m in ALL}\n\n"
        _s += "@classmethod\n"
        _s += "def from_abbreviation(cls, abbreviation: str):\n"
        _s += "\treturn cls.abbreviation_map.get(abbreviation, None)\n"
        return _s

    @staticmethod
    def model_enum_entry(key: str, value: str):
        return "{key} = {instance}()\n".format(key=key, instance=value)

    @staticmethod
    def file_header(source_filename: Union[str, os.PathLike], dt: Optional[datetime.datetime] = None):
        if dt is None:
            dt = datetime.datetime.now(datetime.timezone.utc)
        _s = ""
        _s += "# generated by pydantic-codegen:\n"
        _s += "# \tfilename:  {source_filename}\n".format(source_filename=source_filename)
        _s += "# \ttimestamp: {dt}\n\n".format(dt=dt)
        return _s
