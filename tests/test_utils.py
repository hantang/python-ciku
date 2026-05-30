from ciku.core.utils import byte2uint


def test_byte2uint_preserves_short_little_endian_behavior() -> None:
    assert byte2uint(b"\x34\x12") == 0x1234
    assert byte2uint(b"\x78\x56\x34\x12") == 0x12345678


def test_byte2uint_preserves_big_endian_behavior() -> None:
    assert byte2uint(b"\x12\x34", byteorder="big") == 0x1234


def test_byte2uint_respects_max_len() -> None:
    assert byte2uint(b"\x01\x02\x03", max_len=2) == 0x0201
