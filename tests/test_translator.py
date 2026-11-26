"""Проверки грамматики, вычислений и типизированного XML."""

import unittest
from pathlib import Path
from xml.etree import ElementTree as ET

from configxml.translator import ConfigError, translate


def xml(source):
    return ET.fromstring(translate(source))


class TranslatorTests(unittest.TestCase):
    def test_decimals_and_source_order(self):
        root = xml("5. '5' 0.125")
        self.assertEqual(root.tag, "config")
        self.assertEqual([(n.tag, n.text) for n in root],
                         [("number", "5"), ("string", "5"),
                          ("number", "0.125")])

    def test_nested_lists_and_strings(self):
        root = xml("list('', list(), list(' // <&> ', 0.))")
        self.assertEqual(root[0][0].tag, "string")
        self.assertEqual(len(root[0][1]), 0)
        self.assertEqual(root[0][2][0].text, " // <&> ")
        self.assertEqual(root[0][2][1].text, "0")

    def test_comments_and_empty_document(self):
        self.assertEqual(len(xml("// пустой файл")), 0)
        self.assertEqual(xml("list(1., // первый\n 2.)")[0][1].text, "2")

    def test_expressions_and_constants(self):
        root = xml("def a := 1.5; def b := ^[+ a 1]; "
                   "list(^[* b 2], ^[/ ^[- a 2] 2], ^[len 'кот'])")
        self.assertEqual(root[1].attrib, {"name": "b"})
        self.assertEqual([n.text for n in root[2]], ["5.0", "-0.25", "3"])

    def test_lengths_and_exact_decimal(self):
        root = xml("^[len list(1., list(2., 3.))] ^[len ''] ^[+ 0.1 0.2]")
        self.assertEqual([n.text for n in root], ["2", "0", "0.3"])

    def test_grammar_rejections(self):
        for source in ("5", "-1.", ".2", "2e3", "def X := 1.;",
                       "def a1 := 1.;", "defa := 1.;", "def a = 1.;",
                       "def a := 1.", "list(1.,)", "list(1. 2.)",
                       "list(list(1.)", "'unfinished", '"x"', "a",
                       "^[+ 1]", "^[len 1 2]", "^[% 2 3]", "^[+ 1 2",
                       "1. garbage", "'a\nb'"):
            with self.subTest(source=source), self.assertRaises(ConfigError):
                xml(source)

    def test_semantic_errors(self):
        cases = {"^[+ later 1] def later := 1.;": "неизвестное имя",
                 "def a := 0.; def a := 1.;": "повторное объявление",
                 "^[+ 'x' 2]": "два числа", "^[len 3]": "строку или массив",
                 "^[/ 1 0]": "деление на ноль", "'\x00'": "символ XML"}
        for source, message in cases.items():
            with self.subTest(source=source):
                with self.assertRaisesRegex(ConfigError, message):
                    xml(source)

    def test_position(self):
        with self.assertRaisesRegex(ConfigError, "2:4:"):
            xml("// первая строка\n   @")

    def test_examples(self):
        folder = Path(__file__).resolve().parents[1] / "examples"
        cases = [("library", "limit", "21"), ("studio", "average", "20"),
                 ("garden", "perbed", "4.0")]
        for case, key, expected in cases:
            with self.subTest(case=case):
                root = xml((folder / f"{case}.cfg").read_text("utf-8"))
                path = f"./constant[@name='{key}']/number"
                self.assertEqual(root.findtext(path), expected)
