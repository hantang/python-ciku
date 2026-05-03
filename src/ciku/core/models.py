import re
from dataclasses import dataclass, field


@dataclass
class WordEntry:
    """词库文件单个词结构"""

    word: str  # 词语
    coding: list[str]  # 编码：一般为拼音
    weight: int  # 词频/权重
    is_pinyin: bool = True  # 是否拼音编码
    is_error: bool = False  # 是否解析异常

    def to_str(self, word_sep: str = "\t", code_sep: str = " ", keep_weight: bool = True) -> str:
        coding_str = self.coding_to_str(code_sep)
        weight = self.weight if self.weight and self.weight > 0 else 0
        data = [self.word, coding_str] + ([weight] if keep_weight else [])
        return word_sep.join(map(str, data))

    def coding_to_str(self, code_sep: str = " ") -> str:
        # 拼音、五笔等编码序列使用分隔符拼接
        return code_sep.join(self.coding)


@dataclass
class DictMeta:
    """词库文件元信息：词库名等配置内容"""

    file: str = ""  # 词库文件名
    name: str = ""  # 词库名
    category: str = ""  # 词库分类
    version: str = ""  # 版本
    description: str = ""  # 描述信息
    author: str = ""  # 作者
    examples: list[str] = field(default_factory=list)  # 词库示例
    count: int | str = ""  # 词条数量（可能来自词库文件内置数据）
    count_actual: int = 0  # 实际解析统计词条数据
    count_error: int = 0  # 实际解析统计词条数据

    def _meta_list(self, keep_all: bool) -> list[list[str]]:
        basic_keys = ["词条数量", "解析词数"]
        word_samples = ""
        if self.examples:
            word_samples = " ".join([re.sub(r"\s+", "", v) for v in self.examples])
        meta_list: list[list[str]] = [
            ["词库文件", self.file],
            ["词库名称", self.name],
            ["词库分类", self.category],
            ["词库版本", self.version],
            ["词库作者", self.author],
            ["词库描述", self.description],
            ["词条样例", word_samples],
            ["词条数量", str(self.count)],
            ["解析词数", str(self.count_actual)],
            ["解析异常", str(self.count_error)],
        ]
        out_list = [
            [key, re.sub(r"[\r\n\s，]+", " ", value).strip()]
            for key, value in meta_list
            if keep_all or value or key in basic_keys
        ]
        return out_list

    def _meta_lines(
        self, prefix: str, key_sep: str, line_sep=" ", keep_all: bool = False
    ) -> list[str]:
        meta_list = self._meta_list(keep_all)
        meta_lines = [
            line_sep.join([prefix, key + key_sep, value]).strip() for key, value in meta_list
        ]
        return meta_lines

    def to_str(self, prefix: str = "#", separator: str = ":", keep_all: bool = False) -> str:
        """
        prefix: 行注释
        separator: 字段分隔符
        keep_all: 保留所有字段（包括空白字段）
        """
        meta_lines = self._meta_lines(prefix, separator, keep_all=keep_all)
        return "\n".join(meta_lines).strip()

    def to_list(self, separator: str = ":", keep_all: bool = False) -> list[str]:
        meta_lines = self._meta_lines("", separator, keep_all=keep_all)
        return meta_lines


@dataclass
class DictCell:
    """词库文件"""

    metadata: DictMeta
    words: list[WordEntry] = field(default_factory=list)


@dataclass
class DictField:
    start: int
    end: int | None = None


def _zero_field():
    return DictField(start=0)


@dataclass
class DictStruct:
    """词库文件结构分段"""

    name: DictField = field(default_factory=_zero_field)  # 词库名位置
    category: DictField = field(default_factory=_zero_field)  # 词库分类
    version: DictField = field(default_factory=_zero_field)  # 版本
    description: DictField = field(default_factory=_zero_field)  # 描述信息
    author: DictField = field(default_factory=_zero_field)  # 作者
    examples: DictField = field(default_factory=_zero_field)  # 词库示例
    count: DictField = field(default_factory=_zero_field)  # 词条数量
    code_len: DictField = field(default_factory=_zero_field)  # 编码映射表长度
    code_map: DictField = field(default_factory=_zero_field)  # 编码映射表（一般为拼音）
    words: DictField = field(default_factory=_zero_field)  # 词语列表
    extra: DictField = field(default_factory=_zero_field)  # 额外字段

    def init_end(self, var_list: list[DictField]):
        # 根据后一字段补全end
        n = len(var_list)
        for i in range(1, n):
            if var_list[i]:
                var_list[i - 1].end = var_list[i].start
