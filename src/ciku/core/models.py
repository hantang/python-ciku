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

    def to_str(
        self, field_sep: str = "\t", code_sep: str = " ", word_first: bool = True, keep_weight: bool = True
    ) -> str:
        """词库转换成str
        默认形式：词语、编码（拼音）、权重
        field_sep: 字段之间分隔符
        code_sep: 拼音等编码分组之间分隔符
        word_first: True时 word code {weight} ；False时 code word {weight}
        keep_weight: 输出权重
        """
        coding_str = self._coding_to_str(code_sep)
        weight = self.weight if self.weight and self.weight > 0 else 0
        if word_first:
            data = [self.word, coding_str]
        else:
            data = [coding_str, self.word]

        if keep_weight:
            data.append(str(weight))

        return field_sep.join(data)

    def _coding_to_str(self, code_sep: str) -> str:
        """拼音、五笔等编码序列使用分隔符拼接"""
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

    def _meta_list(
        self,
        example_sep: str,
        is_strip: bool,
        keep_all: bool,
        keep_filename: bool,
    ) -> list[tuple[str, str]]:
        # basic_keys = ["词条数量", "解析词数"]
        word_examples = self._get_word_samples(example_sep, is_strip)

        meta_list: list[list[str]] = [
            ["词库名称", self.name],
            ["词库分类", self.category],
            ["词库版本", self.version],
            ["词库作者", self.author],
            ["词库描述", self.description],
            ["词条样例", word_examples],
            ["词条数量", str(self.count)],
            ["解析词数", str(self.count_actual)],
            ["解析异常", str(self.count_error)],
        ]
        if keep_filename:
            meta_list = [["词库文件", self.file]] + meta_list

        if not keep_all:
            meta_list = [entry for entry in meta_list if entry[1]]

        if is_strip:
            out_list = [(key, self._strip(value)) for key, value in meta_list]
        else:
            out_list = [(key, value) for key, value in meta_list]
        return out_list

    def _get_word_samples(self, sep: str, is_strip: bool) -> str:
        words = [self._strip(v) if is_strip else v for v in self.examples] if self.examples else []
        return sep.join(words)

    def _strip(self, value: str) -> str:
        return re.sub(r"\s+", " ", value).strip()

    def _meta_lines(
        self,
        line_comment: str,
        *,
        field_sep: str,
        key_sep: str,
        example_sep: str,
        is_strip: bool,
        keep_all: bool,
        keep_filename: bool,
    ) -> list[str]:
        meta_list = self._meta_list(example_sep, is_strip, keep_all, keep_filename)
        if line_comment:
            meta_lines = [field_sep.join([line_comment, key + key_sep, value]).strip() for key, value in meta_list]
        else:
            meta_lines = [field_sep.join([key + key_sep, value]).strip() for key, value in meta_list]
        return meta_lines

    def to_list(
        self,
        *,
        separator: str = " ",
        key_sep: str = ":",
        example_sep: str = " ",
        keep_all: bool = False,
        keep_filename: bool = False,
    ) -> list[str]:
        meta_lines = self._meta_lines(
            "",
            field_sep=separator,
            key_sep=key_sep,
            example_sep=example_sep,
            is_strip=False,
            keep_all=keep_all,
            keep_filename=keep_filename,
        )
        return meta_lines

    def to_str(
        self,
        comment: str = "#",
        *,
        separator: str = " ",
        key_sep: str = ":",
        example_sep: str = "、",
        keep_all: bool = False,
        keep_filename: bool = False,
    ) -> str:
        """
        comment: 行注释
        separator/field_sep: 注释、字段键名、取值之间的分隔符
        key_sep: 字段key-value分隔符
        example_sep: 词条样例中词语之间分隔符
        keep_all: 保留所有字段（包括空白字段）
        keep_filename: 保留解析的文件名
        """
        meta_lines = self._meta_lines(
            comment,
            field_sep=separator,
            key_sep=key_sep,
            example_sep=example_sep,
            is_strip=True,
            keep_all=keep_all,
            keep_filename=keep_filename,
        )
        return "\n".join(meta_lines).strip()


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
