from pathlib import Path

import pytest

from ciku import BaiduMobileParser, BaiduParser, HuayuParser, QQParser, QQV1Parser, SogouParser

LOCAL_DATA = "data"

LOCAL_FIXTURES = [
    BaiduParser,
    BaiduMobileParser,
    SogouParser,
    QQParser,
    QQV1Parser,
    HuayuParser,
]


@pytest.mark.parametrize("parser_cls", LOCAL_FIXTURES)
def test_local_binary_fixtures_parse_when_present(parser_cls, tmp_path: Path) -> None:
    parser = parser_cls()
    glob_pattern = f"*.{parser.suffix}"
    files = sorted(Path(LOCAL_DATA).rglob(glob_pattern))
    if not files:
        pytest.skip(f"local private fixtures not present: {glob_pattern}")

    fixture = files[0]
    assert parser.parse(fixture)

    exported = parser.export_data()
    assert exported["meta"]
    assert exported["words"]

    save_file = tmp_path / f"{fixture.stem}.txt"
    assert parser.save_data(save_file)
    assert save_file.exists()
