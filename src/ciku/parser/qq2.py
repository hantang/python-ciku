"""
QQ新版: 格式基本同搜狗(.scel)
- 词库网址: https://cdict.qq.pinyin.cn
- 文件后缀：.qcel
"""

from ..core.models import DictField
from .sogou import SogouParser


class QQParser(SogouParser):
    suffix: str = "qcel"

    def _decode_text(
        self,
        data: bytes,
        offset: DictField | None,
        encoding: str | None = None,
        is_strip: bool = True,
    ) -> str:
        out = super()._decode_text(data, offset, encoding, is_strip)
        return out.split("\x00")[0]
