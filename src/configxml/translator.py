"""Вычисление выражений и построение XML-документа."""

import operator
import re
from decimal import Context, Decimal, DecimalException, localcontext
from xml.etree import ElementTree as ET

import pyparsing as pp

from .grammar import GRAMMAR, Node


class ConfigError(ValueError):
    """Ошибка исходного документа с позицией и фрагментом текста."""


OPS = {"+": operator.add, "-": operator.sub, "*": operator.mul,
       "/": operator.truediv}
BAD_XML = re.compile(r"[^\x09\x0a\x0d\x20-\ud7ff\ue000-\ufffd"
                     r"\U00010000-\U0010ffff]")
PRECISION = 28


def problem(source, loc, message):
    """Подготовить сообщение в координатах исходного файла."""
    row, col = pp.lineno(loc, source), pp.col(loc, source)
    prefix = pp.line(loc, source)[:col - 1]
    pointer = "".join("\t" if ch == "\t" else " " for ch in prefix)
    return ConfigError(
        f"{row}:{col}: {message}\n{pp.line(loc, source)}\n{pointer}^"
    )


def calculate(op, args):
    """Проверить типы и вычислить префиксный оператор."""
    if op == "len":
        if not isinstance(args[0], (str, list)):
            raise ValueError("len ожидает строку или массив")
        return Decimal(len(args[0]))
    if not all(isinstance(arg, Decimal) for arg in args):
        raise ValueError(f"операция {op} ожидает два числа")
    if op == "/" and args[1].is_zero():
        raise ValueError("деление на ноль")
    try:
        return OPS[op](*args)
    except DecimalException as exc:
        raise ValueError("результат вне диапазона Decimal") from exc


def evaluate(item, names, source):
    """Вычислить узел, используя ранее объявленные константы."""
    if not isinstance(item, Node):
        return item
    if item.kind == "ref":
        name, = item.parts
        if name not in names:
            raise problem(source, item.offset, f"неизвестное имя {name}")
        return names[name]
    if item.kind == "list":
        return [evaluate(part, names, source) for part in item.parts]
    op, *parts = item.parts
    args = [evaluate(part, names, source) for part in parts]
    try:
        return calculate(op, args)
    except ValueError as exc:
        raise problem(source, item.offset, str(exc)) from exc


def append_value(parent, value):
    """Записать значение с явным XML-тегом типа."""
    if isinstance(value, list):
        array = ET.SubElement(parent, "list")
        for item in value:
            append_value(array, item)
    elif isinstance(value, Decimal):
        ET.SubElement(parent, "number").text = str(value)
    else:
        ET.SubElement(parent, "string").text = value


def emit(item, root, names, source):
    """Добавить объявление или самостоятельное значение."""
    if isinstance(item, Node) and item.kind == "def":
        name, item_value = item.parts
        if name in names:
            raise problem(source, item.offset, f"повторное объявление {name}")
        names[name] = evaluate(item_value, names, source)
        append_value(ET.SubElement(root, "constant", name=name), names[name])
    else:
        append_value(root, evaluate(item, names, source))


def translate(source):
    """Вернуть готовый XML в UTF-8 или вызвать ConfigError."""
    invalid = BAD_XML.search(source)
    if invalid:
        raise problem(source, invalid.start(), "недопустимый символ XML 1.0")
    root, names = ET.Element("config"), {}
    try:
        with localcontext(Context(prec=PRECISION)):
            for item in GRAMMAR.parse_string(source, parse_all=True):
                emit(item, root, names, source)
    except pp.ParseBaseException as exc:
        raise problem(source, exc.loc, "синтаксическая ошибка") from exc
    except RecursionError as exc:
        raise ConfigError("превышена допустимая глубина вложенности") from exc
    ET.indent(root)
    return ET.tostring(root, encoding="utf-8", xml_declaration=True) + b"\n"
