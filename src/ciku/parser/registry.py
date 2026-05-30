from ..core.base import BaseParser
from .baidu import BaiduMobileParser, BaiduParser
from .huayu import HuayuParser
from .qq import QQV1Parser
from .qq2 import QQParser
from .sogou import SogouParser

PARSER_CLASSES: tuple[type[BaseParser], ...] = (
    SogouParser,
    BaiduParser,
    BaiduMobileParser,
    QQParser,
    QQV1Parser,
    HuayuParser,
)
