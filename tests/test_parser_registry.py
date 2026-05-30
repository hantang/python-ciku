import ciku
from ciku.cli import ParserFactory
from ciku.parser.registry import PARSER_CLASSES


def test_descriptive_parser_names_are_public_aliases() -> None:
    assert ciku.SogouScelParser is ciku.SogouParser
    assert ciku.BaiduPinyinBdictParser is ciku.BaiduParser
    assert ciku.BaiduMobileBcdParser is ciku.BaiduMobileParser
    assert ciku.QQPinyinQcelParser is ciku.QQParser
    assert ciku.QQPinyinQpydParser is ciku.QQV1Parser


def test_parser_registry_contains_each_supported_suffix_once() -> None:
    assert [parser.suffix for parser in PARSER_CLASSES] == ["scel", "bdict", "bcd", "qcel", "qpyd", "uwl"]


def test_parser_factory_uses_registry_by_default() -> None:
    factory = ParserFactory()

    assert sorted(factory.get_suffixes()) == ["bcd", "bdict", "qcel", "qpyd", "scel", "uwl"]
    assert factory.get_parser(".scel") is ciku.SogouScelParser
