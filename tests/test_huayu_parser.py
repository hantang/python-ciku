from ciku.parser.huayu import HuayuParser


def test_huayu_invalid_empty_segment_returns_no_entries() -> None:
    parser = HuayuParser()

    assert parser.parse_segment(b"\x00" * parser.struct.seg_header, index=0) == []
