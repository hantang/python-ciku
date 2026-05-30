from pathlib import Path
from argparse import ArgumentTypeError

import pytest

import ciku
from ciku.cli import ParserToolkit, ProcessSummary, positive_int, process


def test_positive_int_rejects_zero() -> None:
    with pytest.raises(ArgumentTypeError):
        positive_int("0")


def test_process_returns_structured_summary_for_empty_directory(tmp_path: Path) -> None:
    summary = process(
        "",
        str(tmp_path),
        str(tmp_path / "out"),
        workers=1,
        keep_error=False,
        is_recursive=False,
        overwrite=False,
    )

    assert summary == ProcessSummary(discovered=0, queued=0, ignored=0, succeeded=0, failed=0, by_suffix={})


def test_parser_toolkit_registers_public_parser_suffixes() -> None:
    assert sorted(ParserToolkit().suffixes) == ["bcd", "bdict", "qcel", "qpyd", "scel", "uwl"]


def test_public_parser_aliases_are_explicit() -> None:
    assert ciku.BaiduPCParser is ciku.BaiduParser
    assert ciku.QQV2Parser is ciku.QQParser
