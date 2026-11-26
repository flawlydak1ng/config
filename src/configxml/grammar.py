"""Грамматика варианта 25 и узлы с позициями в исходном тексте."""

from dataclasses import dataclass
from decimal import Decimal

import pyparsing as pp


@dataclass(frozen=True)
class Node:
    kind: str
    offset: int
    parts: tuple


def tagged(expr, kind):
    """Сохранить вид конструкции, позицию и дочерние элементы."""
    def build(source, loc, tokens):
        return Node(kind, loc, tuple(tokens))

    return expr.set_parse_action(build)


def make_grammar():
    """Построить рекурсивную грамматику документа."""
    sym = pp.Suppress
    name = pp.Regex("[a-z]+")
    value, expr = pp.Forward(), pp.Forward()
    number = pp.Regex(r"[0-9]+\.[0-9]*").set_parse_action(
        lambda t: Decimal(t[0])
    )
    integer = pp.Regex(r"[0-9]+").set_parse_action(lambda t: Decimal(t[0]))
    string = pp.Regex(r"'[^'\r\n]*'").set_parse_action(lambda t: t[0][1:-1])
    items = pp.Optional(pp.DelimitedList(value))
    list_head = sym(pp.Keyword("list")) + sym("(")
    array = tagged(list_head - items - sym(")"), "list")
    reference = tagged(name.copy(), "ref")
    operand = value | integer | reference
    binary = pp.one_of("+ - * /") - operand - operand
    length = pp.Keyword("len") - operand
    expr <<= tagged(sym("^[") - (binary | length) - sym("]"), "expr")
    value <<= number | string | array | expr
    head = sym(pp.Keyword("def")) - name - sym(":=")
    decl = tagged(head - value - sym(";"), "def")
    document = pp.ZeroOrMore(decl | value) + pp.StringEnd()
    document.ignore(pp.Regex(r"//[^\n]*"))
    return document.parse_with_tabs()


GRAMMAR = make_grammar()
