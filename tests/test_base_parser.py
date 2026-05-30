from pathlib import Path

from ciku.core.base import BaseParser
from ciku.core.models import DictCell, DictMeta, WordEntry


class DummyParser(BaseParser):
    suffix = "dummy"
    code_map = {1: "yi"}

    def parse(self, file_path: Path | str) -> bool:
        return False

    def extract_meta(self, data: bytes) -> DictMeta:
        return DictMeta()

    def extract_words(self, data: bytes, allow_error: bool = False) -> list[WordEntry]:
        return []


def test_base_parser_uses_instance_state_for_mutable_fields() -> None:
    first = DummyParser()
    second = DummyParser()

    first.code_map[2] = "er"
    first.current_file = "first.dummy"
    first.dict_cell = DictCell(DictMeta())

    assert second.code_map == {1: "yi"}
    assert second.current_file == ""
    assert second.dict_cell is None


def test_has_invalid_pinyin_matches_actual_semantics() -> None:
    parser = DummyParser()

    assert parser._has_invalid_pinyin(["zhong", "guo"]) is False
    assert parser._has_invalid_pinyin(["not-a-pinyin"]) is True
