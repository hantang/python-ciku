from ciku.parser.sogou import SogouParser


def test_sogou_extract_extra_words_decodes_full_word() -> None:
    parser = SogouParser()
    data = b"".join(
        [
            (1).to_bytes(2, "little"),  # extra word count
            (2).to_bytes(2, "little"),  # character count
            "测试".encode("utf-16le"),
        ]
    )

    [entry] = parser.extract_extra_words(data)

    assert entry.word == "测试"
    assert entry.coding == []
    assert entry.is_error is True
