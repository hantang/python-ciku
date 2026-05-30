import pytest

from ciku.parser.baidu import BaiduParser


def test_baidu_special_entry_with_matching_pinyin_is_not_error() -> None:
    parser = BaiduParser()
    data = b"".join(
        [
            (0).to_bytes(2, "little"),  # special entry marker
            (0).to_bytes(2, "little"),  # weight
            (9).to_bytes(2, "little"),  # chong'shi
            (2).to_bytes(2, "little"),  # 词库
            "chong'shi".encode("utf-16le"),
            "词库".encode("utf-16le"),
        ]
    )

    [entry] = parser.extract_words(data)

    assert entry.word == "词库"
    assert entry.coding == ["chong", "shi"]
    assert entry.is_error is False


def test_baidu_pinyin_decode_error_uses_fallback_marker(monkeypatch: pytest.MonkeyPatch) -> None:
    parser = BaiduParser()

    def raise_decode_error(data: bytes, strip: bool = True) -> str:
        raise UnicodeDecodeError("utf-16le", data, 0, 1, "test decode error")

    monkeypatch.setattr(parser, "_decode_data", raise_decode_error)

    assert parser._parse_pinyin(bytes([255, 255])) == ["?"]
