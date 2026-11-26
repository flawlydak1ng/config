"""Интерфейс командной строки для перевода конфигурации в XML."""

import argparse
import os
import sys
from pathlib import Path
from tempfile import NamedTemporaryFile

from .translator import ConfigError, translate


def save(path, data):
    """Атомарно заменить файл после успешного вычисления документа."""
    with NamedTemporaryFile(dir=path.parent, delete=False) as stream:
        temporary = Path(stream.name)
        try:
            stream.write(data)
            stream.close()
            os.replace(temporary, path)
        finally:
            temporary.unlink(missing_ok=True)


def main(argv=None):
    """Прочитать входной файл и вернуть код завершения CLI."""
    parser = argparse.ArgumentParser(description="Перевод конфигурации в XML")
    parser.add_argument("-i", "--input", required=True, type=Path,
                        help="входной файл UTF-8")
    parser.add_argument("-o", "--output", required=True, type=Path,
                        help="выходной XML-файл")
    args = parser.parse_args(argv)
    try:
        if args.output.exists() and args.input.samefile(args.output):
            raise ValueError("входной и выходной файлы совпадают")
        source = args.input.read_text(encoding="utf-8-sig")
        save(args.output, translate(source))
    except ConfigError as exc:
        print(f"{args.input}:{exc}", file=sys.stderr)
        return 1
    except (OSError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
