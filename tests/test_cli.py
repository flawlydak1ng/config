"""Проверки интерфейса через запуск отдельного процесса."""

import subprocess
import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from xml.etree import ElementTree as ET


class CliTests(unittest.TestCase):
    def setUp(self):
        folder = TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        self.source = Path(folder.name) / "мой файл.cfg"
        self.output = Path(folder.name) / "результат.xml"

    def invoke(self, *args):
        return subprocess.run([sys.executable, "-m", "configxml", *args],
                              capture_output=True, text=True, check=False)

    def convert(self):
        return self.invoke("--input", self.source, "--output", self.output)

    def test_file_conversion(self):
        self.source.write_text("'текст & <xml>'", encoding="utf-8-sig")
        result = self.convert()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout, "")
        self.assertEqual(ET.parse(self.output).getroot()[0].text,
                         "текст & <xml>")

    def test_previous_file_survives_error(self):
        self.source.write_text("def x := ;", encoding="utf-8")
        self.output.write_bytes(b"old")
        result = self.convert()
        self.assertEqual(result.returncode, 1)
        self.assertIn("1:10:", result.stderr)
        self.assertEqual(self.output.read_bytes(), b"old")

    def test_missing_input_and_flags(self):
        self.assertEqual(self.convert().returncode, 1)
        self.assertFalse(self.output.exists())
        self.assertEqual(self.invoke("-i", self.source).returncode, 2)

    def test_invalid_unicode_and_same_file(self):
        self.source.write_bytes(b"\xff")
        self.assertEqual(self.convert().returncode, 1)
        self.source.write_bytes(b"1.")
        result = self.invoke("-i", self.source, "-o", self.source)
        self.assertEqual(result.returncode, 1)
        self.assertEqual(self.source.read_bytes(), b"1.")

    def test_output_directory_missing(self):
        self.source.write_bytes(b"1.")
        self.output = self.output / "file.xml"
        self.assertEqual(self.convert().returncode, 1)
