from .baidu import BaiduMobileParser, BaiduParser
from .huayu import HuayuParser
from .qq import QQV1Parser
from .qq2 import QQParser
from .sogou import SogouParser

# descriptive aliases, add suffix
SogouScelParser = SogouParser
BaiduPinyinBdictParser = BaiduParser
BaiduPCParser = BaiduParser
BaiduMobileBcdParser = BaiduMobileParser
QQPinyinQcelParser = QQParser
QQV2Parser = QQParser
QQPinyinQpydParser = QQV1Parser

__all__ = [
    "SogouParser",
    "SogouScelParser",
    "BaiduParser",
    "BaiduPinyinBdictParser",
    "BaiduPCParser",
    "BaiduMobileParser",
    "BaiduMobileBcdParser",
    "QQParser",
    "QQPinyinQcelParser",
    "QQV1Parser",
    "QQV2Parser",
    "QQPinyinQpydParser",
    "HuayuParser",
]
