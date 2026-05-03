"""
搜狗输入法
- 词库网址: https://pinyin.sogou.com/dict/
- 文件后缀: .scel

参考资料
- https://nopdan.com/2022/05/02-sogou-scel/
- https://github.com/nopdan/rose/blob/main/pkg/pinyin/sogou_scel.go
- https://github.com/StuPeter/Sougou_dict_spider/blob/master/Scel2Txt.py
- https://github.com/studyzy/imewlconverter/blob/master/src/ImeWlConverterCore/IME/SougouPinyinScel.cs

文件格式
范围	描述
0x000 - 0x11F	未知
0x120 - 0x123	a, 不展开重码的词条数（编码数）
0x124 - 0x127	b, 展开重码的词条数（词数）
0x128 - 0x12B	未知，和 a 有关
0x12C - 0x12F	未知，和 b 有关
0x130 - 0x337	词库名
0x338 - 0x53F	词库类型
0x540 - 0xD3F	备注/描述信息
0xD40 - 0x153F	示例词
0x1540 拼音表的长度(前两字节)
0x1544 拼音表正文（索引 + 长度 + 拼音编码）
0x2628 词库正文

#TODO 解析异常：Out of bound
人文科学/文学/网络流行新词.scel
娱乐/其它/流行网络小说词库-52440.scel
"""

import logging
from pathlib import Path

from ..core.base import BaseParser
from ..core.models import DictCell, DictField, DictMeta, DictStruct, WordEntry
from ..core.utils import byte2str, byte2uint


def _check_extra_word(data: bytes, pos: int, step: int, encoding: str) -> int:
    word = "DELTBL"
    code_len = len(word) * step
    if pos + code_len <= len(data) and byte2str(data[pos : pos + code_len], encoding, False) == word:
        return code_len
    return 0


class SogouDictStruct(DictStruct):
    def __init__(self):
        super().__init__(
            name=DictField(start=0x130),
            category=DictField(start=0x338),
            description=DictField(start=0x540),
            examples=DictField(start=0xD40),
            code_len=DictField(start=0x1540),
            code_map=DictField(start=0x1544),
            words=DictField(start=0x2628),
        )
        attributes = [
            self.name,
            self.category,
            self.description,
            self.examples,
            self.code_len,
            self.code_map,
        ]
        self.init_end(attributes)


class SogouParser(BaseParser):
    suffix = "scel"
    encoding = "utf-16le"
    struct = SogouDictStruct()

    def parse(self, file_path: Path | str) -> bool:
        self.dict_cell = None
        file_path = Path(file_path)
        self.current_file = file_path.as_posix()
        data = self._read_data(file_path)
        if not self.check(data):
            return False

        self.code_map, start = self.init_code_map(data)
        word_data = data[start:]
        words = self.extract_words(word_data)

        metadata = self.extract_meta(data)
        metadata.file = file_path.name
        metadata.count_actual = len(words)
        metadata.count_error = sum(1 for w in words if w.is_error)

        self.dict_cell = DictCell(metadata, words)
        return True

    def check(self, data: bytes | None) -> bool:
        if data and data[:1] != b"@":
            logging.error(f" {self.current_file} 文件格式不符{self.suffix}规范")
            return False
        return super().check(data)

    def extract_meta(self, data: bytes) -> DictMeta:
        struct = self.struct
        name = self._decode_text(data, struct.name)
        category = self._decode_text(data, struct.category)
        description = self._decode_text(data, struct.description)
        examples = self._decode_text(data, struct.examples).split()
        metadata = DictMeta(
            name=name,
            category=category,
            description=description,
            examples=examples,
        )

        logging.debug(f"词库 = {name} / 分类 = {category}")
        return metadata

    def extract_words(self, data: bytes, allow_error: bool = False) -> list[WordEntry]:
        step = self.step
        encoding = self.encoding
        pinyin_dict = self.code_map
        extra_flag = b"DELTBL"
        word_data = data

        word_list = []
        pos = 0
        has_extra = data.find(extra_flag)
        extra_data = b""
        if has_extra >= 0:
            logging.warning("存在额外词库列表")
            extra_data = data[has_extra + len(extra_flag) :]
            word_data = data[:has_extra]

        total = len(word_data)
        while pos < total:
            # 判断是否有额外词部分
            if step2 := _check_extra_word(word_data, pos, step, encoding):
                pos += step2
                has_extra = True
                break

            homonym_count = byte2uint(word_data[pos : pos + step])  # 同音词个数
            pinyin_index_len = byte2uint(word_data[pos + step : pos + step * 2])
            pos += step * 2
            if pinyin_index_len > 100:
                logging.debug(f"拼音长度异常 {pinyin_index_len}")
                # group = word_data[pos:].find(b"\x00" * 8) # 尝试寻找新开始点

            # 拼音
            pinyin_list = []
            for i in range(0, pinyin_index_len, step):
                index = byte2uint(word_data[pos + i : pos + i + step])
                if index >= len(pinyin_dict):
                    # 拼音越界出错: 提前终止？
                    logging.debug(f"Out of bound = {index}/{len(pinyin_dict)}")
                pinyin_list.append(pinyin_dict.get(index, "*"))
            pos += pinyin_index_len

            # 词语
            for _ in range(homonym_count):
                char_len = byte2uint(word_data[pos : pos + step])
                word = self._decode_text(word_data[pos + step : pos + step + char_len], None, None, False)
                pos += step + char_len

                if char_len != pinyin_index_len and word:
                    # 一般包含非中文字符
                    word = word.strip(" \u3000")
                    logging.debug(f"词语字数和拼音长度不一致: {word}, {' '.join(pinyin_list)}")

                # 扩展部分（共2+10字节）: 前2字节可能词频（或权重、序号），剩余8字节未知 一般都是\x00
                ext_len = byte2uint(word_data[pos : pos + step])  # 扩展长度，都是10
                weight = byte2uint(word_data[pos + step : pos + step * 2])  # 前2字节作为权重
                pos += step + ext_len
                if not word:
                    continue

                is_error = self._check_pinyin(pinyin_list)
                entry = WordEntry(word, pinyin_list, weight, is_error=is_error)
                word_list.append(entry)

        logging.debug(f"Word list = {len(word_list)}")

        extra_word_list = self.extract_extra_words(extra_data) if allow_error else []
        if extra_word_list:
            logging.warning(f"额外词库列表 = {len(extra_word_list)}")
            word_list += extra_word_list

        return word_list

    def extract_extra_words(self, data: bytes) -> list[WordEntry]:
        # 剩余额外词部分（黑名单/删除词）: 只有词，没有拼音等部分, eg: 城市信息大全/广东/珠海地域名称.scel
        extra_word_list = []
        step = self.step
        word_data = data

        pos = 0
        block_len = byte2uint(word_data[pos : pos + step])  # 2字节表示词库词条数
        pos += step
        for _ in range(block_len):
            char_count = byte2uint(word_data[pos : pos + step])  # 词语对应字数
            pos += step
            word = self._decode_text(word_data[pos + step : pos + step * char_count], None, None, False)
            pos += step * char_count

            entry = WordEntry(word, [], 0, is_error=True)
            extra_word_list.append(entry)
        return extra_word_list

    def init_code_map(self, data: bytes) -> tuple[dict, int]:
        step = self.step
        struct = self.struct

        data_pinyin_len = data[struct.code_len.start : struct.code_len.end]
        pinyin_data = data[struct.code_map.start : struct.code_map.end]

        pinyin_dict = {}
        pos = 0
        pinyin_len = byte2uint(data_pinyin_len)  # 一般拼音表长度 413，部分是414组
        if pinyin_len != 413:
            logging.debug(f"pinyin dict is {pinyin_len}")

        for _ in range(pinyin_len):
            py_index, py_value, pos = self._decode_pinyin(pinyin_data, pos, step)
            pinyin_dict[py_index] = py_value
            if pos > len(pinyin_data):
                break
        if len(pinyin_dict) != pinyin_len:
            logging.warning(f"拼音映射表不一致 {len(pinyin_dict)}/{pinyin_len}")

        # 拼音表结束位置（词表开始，默认固定值部分文件可能有问题）
        pos_end = struct.code_map.start + pos
        return pinyin_dict, pos_end

    def _decode_pinyin(self, pinyin_data: bytes, pos: int, step: int, is_strip: bool = True) -> tuple[int, str, int]:
        encoding = self.encoding
        py_index = byte2uint(pinyin_data[pos : pos + step])
        py_len = byte2uint(pinyin_data[pos + step : pos + step * 2])
        pos += step * 2
        py_value = byte2str(pinyin_data[pos : pos + py_len], encoding, is_strip)
        pos += py_len
        return py_index, py_value, pos
