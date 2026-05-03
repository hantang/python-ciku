from .baidu import BaiduMobileParser, BaiduParser
from .huayu import HuayuParser
from .qq import QQV1Parser
from .qq2 import QQParser
from .sogou import SogouParser
# alias
from .baidu import BaiduParser as BaiduPCParser
from .qq2 import QQParser as QQV2Parser


__all__ = [
    "SogouParser",
    "BaiduParser",
    "BaiduPCParser",
    "BaiduMobileParser",
    "QQParser",
    "QQV1Parser",
    "QQV2Parser",
    "HuayuParser",
]
