"""
QQ v1（6.0以下版本词库）: 没有拼音映射表，直接拼音编码；中间词库部分使用zlib压缩
- 词库网址：https://cdict.qq.pinyin.cn/v1/
- 文件后缀：.qpyd

参考资料：
- https://nopdan.com/2022/05/06-qq-qpyd/
- https://github.com/WuLC/ThesaurusParser
- https://www.biaodianfu.com/ime-dict-decoder.html

格式：
0x38 2字节 词库（zlib压缩）起始位置
0x44 词库词条数量
0x60~ 词库描述信息

词库部分：前部编码索引 + 后部词库信息
1B: 拼音长度
1B: 词语字节数
4B: 都是 00 00 80 3F
4B: 词条索引
"""

import logging
import zlib
from pathlib import Path

from ..core.base import BaseParser
from ..core.models import DictCell, DictField, DictMeta, DictStruct, WordEntry
from ..core.utils import byte2uint


class QQV1DictStruct(DictStruct):
    def __init__(self):
        super().__init__(
            count=DictField(start=0x44, end=0x48),
            description=DictField(start=0x60),  # 词库名、分类等都合并在一起编码
            extra=DictField(start=0x38, end=0x3C),  # 词语列表开始位置
        )


class QQV1Parser(BaseParser):
    suffix = "qpyd"
    encoding = "utf-16le"
    struct = QQV1DictStruct()
    offset_word: int = 0
    count: int = 0

    def check(self, data: bytes | None) -> bool:
        if data and data[:4] != b"\x09\xa6\x1e\x7d":
            logging.error(f"文件前缀格式不符合: {self.current_file}")
            return False
        return super().check(data)

    def parse(self, file_path: Path | str) -> bool:
        self.dict_cell = None
        file_path = Path(file_path)
        data = self._read_data(file_path)
        if not self.check(data):
            return False
        struct = self.struct
        self.offset_word = byte2uint(data[struct.extra.start : struct.extra.end])
        self.count = byte2uint(data[struct.count.start : struct.count.end])

        word_data = self.decompress_data(data)
        words = self.extract_words(word_data)

        metadata = self.extract_meta(data)
        metadata.file = file_path.name
        metadata.count_actual = len(words)
        metadata.count_error = sum(1 for w in words if w.is_error)

        self.dict_cell = DictCell(metadata, words)
        return True

    def extract_meta(self, data: bytes) -> DictMeta:
        struct = self.struct
        offset_word = self.offset_word
        count = self.count
        data_info = self._decode_text(data[struct.description.start : offset_word], None)
        logging.debug(f"data info = \n{data_info}")

        data_entries = [val for line in data_info.split("\r\n") if (val := line.strip())]
        data_pairs = [val.split(":", 1) for val in data_entries]
        data_info_dict = {pair[0]: pair[1].lstrip() for pair in data_pairs if len(pair) == 2}

        name = data_info_dict.get("Name", "")
        category = " ".join([data_info_dict.get(cate_key, "") for cate_key in ["Type", "FirstType"]]).strip()
        description = data_info_dict.get("Intro", "")
        examples = data_info_dict.get("Example", "").split()
        metadata = DictMeta(
            name=name,
            category=category,
            description=description,
            examples=examples,
            count=count,
        )

        logging.debug(f"词库 = {name} / 分类 = {category}")
        return metadata

    def extract_words(self, data: bytes, allow_error: bool = False) -> list[WordEntry]:
        step = 10
        word_data = data
        count = self.count
        weight = 0  # 词库中没有权重

        word_list = []
        pos = 0
        for _ in range(count):
            # 第1字节拼音长度，第2字节词语字节数，3-6字节未知（00 00 80 3F），7-10字节词索引
            pinyin_len = byte2uint(word_data[pos : pos + 1])
            word_len = byte2uint(word_data[pos + 1 : pos + 2])
            word_index = byte2uint(word_data[pos + 6 : pos + step])
            pos += step
            word_index2 = word_index + pinyin_len
            if word_index2 + word_len > len(word_data):
                logging.warning("词语索引异常越界")
                break

            pinyin_data = word_data[word_index:word_index2]
            pinyin_list = pinyin_data.decode("utf-8").split("'")  # 自带'进行分割
            word = self._decode_text(word_data[word_index2 : word_index2 + word_len], None, None, False)
            is_error = len(pinyin_data) == len(pinyin_list) or self._has_invalid_pinyin(pinyin_list)
            entry = WordEntry(word, pinyin_list, weight, is_error=is_error)
            word_list.append(entry)

        logging.debug(f"word list = {len(word_list)}")
        return word_list

    def decompress_data(self, data: bytes) -> bytes:
        compressed_data = data[self.offset_word :]
        try:
            word_data = zlib.decompress(compressed_data)
        except zlib.error as e:
            logging.error(f"zlib解压失败 {e}")  # TODO
            raise
        return word_data
