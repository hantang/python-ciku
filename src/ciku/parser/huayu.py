"""
华宇（紫光）拼音
- 词库网址：http://srf.unispim.com/wordlib/index.php
- 文件后缀：.uwl

参考资料：
- https://nopdan.com/2022/05/03-ziguang-uwl/
- https://github.com/studyzy/imewlconverter/blob/master/src/ImeWlConverterCore/IME/ZiGuangPinyinUwl.cs

特点：
拼音表不在词库中
编码可能是gbk或utf-16le
uwl文件可能是压缩文件rar/zip，压缩文件中可能为txt文件（gbk/gb2312编码，只有词语没有拼音）

格式：
0x04 - 0x23	词库名
0x24 - 0x43	词库作者
0x44 - 0x47	词条数
0x48 - 0x4B	段数
0x4C - 0xBFF 未知
# 词库
从 0xC00 开始，1024字节*段数，每段=16字节的头信息(4字节一段) + 词条
    前4个字节是段序号（从0开始），
    之后4个字节都是b'\xff\xff\xff\xff'
    之后4字节未知
    最后4字节：词条字节数N(词条实际范围：0x10~0x10+N)

# 解析异常
rar文件：人名/古今名人/人名词库9.1.uwl
rar文件（内部是doc）：其它/未归类/医学-法医学.uwl
zip文件（内部是txt, gbk编码）：地名/上海地名.uwl
拼音解析越界：其它/综合词库/★林激异冻★【综合词库】.uwl
"""

import logging
from os import PathLike
from pathlib import Path

from ..core.base import BaseParser
from ..core.models import DictCell, DictField, DictMeta, DictStruct, WordEntry
from ..core.utils import byte2uint
from ..pinyin.huayu import HUAYU_PINYIN_FINALS as PINYIN_FINALS
from ..pinyin.huayu import HUAYU_PINYIN_INITIALS as PINYIN_INITIALS

# def read_rarfile(rar_file, suffix) -> bytes:
#     """
#     pip install rarfile
#     额外依赖unrar/unar
#     brew install unar
#     """
#     import rarfile
#
#     with rarfile.RarFile(rar_file) as rf:
#         names = rf.namelist()
#         names_valid = [name for name in names if name.endswith(suffix)]
#         print(names_valid)
#         if not names_valid:
#             logging.error(f"suffix={suffix} name file is None: {names}")
#             return None
#         filename = names_valid[0]
#         logging.info(f"文件名为 = {filename}")
#         with rf.open(filename) as f:
#             data = f.read()
#     return data


def read_zipfile(
    file: str | PathLike[str], suffix: str, encoding: str | None = "gbk", file_index: int = 0
) -> bytes | None:
    import zipfile

    with zipfile.ZipFile(file, mode="r", metadata_encoding=encoding) as zf:  # type: ignore
        names = zf.namelist()
        # name.encode("cp437").decode("gbk")
        names_valid = [name for name in names if name.endswith(suffix)]
        if not names_valid:
            logging.warning(f"{suffix}文件内缺少压缩文件: {names}")
            return None

        filename = names_valid[file_index]
        logging.info(f"选择第{file_index}个文件 = {filename}")
        with zf.open(filename) as f:
            data = f.read()

    return data


class HuayuDictStruct(DictStruct):
    def __init__(self):
        super().__init__(
            name=DictField(start=0x04),
            author=DictField(start=0x24),
            count=DictField(start=0x44),
            extra=DictField(start=0x48, end=0x4C),  # 3/4字节
            words=DictField(start=0xC00),
        )
        self.encoding_type = DictField(start=0x02)
        self.seg_header = 0x10
        self.seg_len = 1024  # 分成若干段，每段长度1024

        attributes = [
            self.encoding_type,
            self.name,
            self.author,
            self.count,
            self.extra,
        ]
        self.init_end(attributes)


class HuayuParser(BaseParser):
    suffix = "uwl"
    encoding = "utf-16le"
    struct = HuayuDictStruct()

    initial_count = len(PINYIN_INITIALS)
    final_count = len(PINYIN_FINALS)
    code_map: dict[int, str] = {i: v for i, v in enumerate(PINYIN_INITIALS + PINYIN_FINALS)}

    def parse(self, file_path: Path | str) -> bool:
        self.dict_cell = None
        file_path = Path(file_path)
        self.current_file = file_path.as_posix()
        struct = self.struct
        data = self._preprocess(file_path)
        if not self.check(data):
            return False

        assert data is not None
        self.encoding = self._init_encoding(data)
        logging.debug(f"encoding = {self.encoding}")

        word_data = data[struct.words.start :]
        seg_count = byte2uint(data[struct.extra.start : struct.extra.end])
        if seg_count * struct.seg_len != len(word_data):
            logging.warning("分段长度不一致")
        words = self.extract_words(word_data)

        metadata = self.extract_meta(data)
        metadata.file = file_path.name
        metadata.count_actual = len(words)
        metadata.count_error = sum(1 for w in words if w.is_error)

        self.dict_cell = DictCell(metadata, words)
        return True

    def check(self, data: bytes | None) -> bool:
        if data and data[:4] not in [b"\x94\x19\x08\x14", b"\x94\x19\x09\x14"]:
            logging.error(f" {self.current_file} 文件格式不符{self.suffix}规范")
            return False
        return super().check(data)

    def _preprocess(self, file_path: Path) -> bytes | None:
        data = self._read_data(file_path)
        if data:
            if data[:2] == b"PK":
                logging.warning(f"文件格式为ZIP，解压处理中：{file_path}")
                zip_data = read_zipfile(file_path, self.suffix)
                if not zip_data:
                    return None
                data = zip_data
            elif data[:4] == b"Rar!":
                logging.error(f"文件格式为RAR，请先解压：{file_path}")
                # data = read_rarfile(file_path, self.suffix)
                return None
        return data

    def extract_meta(self, data: bytes) -> DictMeta:
        struct = self.struct
        name = self._decode_text(data, struct.name)
        author = self._decode_text(data, struct.author)
        count = byte2uint(data[struct.count.start : struct.count.end])

        metadata = DictMeta(
            name=name,
            author=author,
            count=count,
        )

        logging.debug(f"词库 = {name}")
        return metadata

    def extract_words(self, data: bytes, allow_error: bool = False) -> list[WordEntry]:
        part_len = self.struct.seg_len
        word_data = data
        word_list = []
        for i in range(0, len(word_data), part_len):
            part = word_data[i : i + part_len]
            out = self.parse_segment(part, i // part_len)
            word_list.extend(out)
        return word_list

    def parse_segment(self, data: bytes, index: int) -> list[WordEntry]:
        header_len = self.struct.seg_header
        step = self.step
        block_len = step * 2  # 4字节

        seg_index = byte2uint(data[:block_len])
        max_len = byte2uint(data[header_len - block_len : header_len])
        if max_len <= 0:
            logging.warning("词库文件解析，分段长度为空")
            return []
        if header_len + max_len > len(data):
            logging.warning("词库文件解析，分段长度越界")
            return []
        word_part = data[header_len : header_len + max_len]
        if index != seg_index:
            logging.warning("词库文件解析，分段索引不匹配")

        word_list = []
        pos = 0
        while pos + block_len < max_len:
            # 前4字节
            a, b = word_part[pos], word_part[pos + 1]  # 拼音、词长度
            weight = byte2uint(word_part[pos + step : pos + block_len])  # 词频2字节
            pinyin_len = (b % 0x10 * 2 + a // 0x80) * 2
            word_len = a % 0x80 - 1  # 取模，避免可能大于 0x80
            if word_len % 2 != 0:  # 少量可能异常，中文双字节编码
                word_len += 1

            pos += block_len
            if pos + pinyin_len > max_len:
                break

            # 拼音(声母、韵母各1字节)
            pinyin_data = word_part[pos : pos + pinyin_len]
            pinyin_list, valid = self._parse_pinyin(pinyin_data)
            pos += pinyin_len
            if pos + word_len > max_len:
                break

            # 词语
            # word_len_fix = word_len  # min(word_len, pinyin_len)
            word_data = word_part[pos : pos + word_len]
            word = self._decode_word(word_data)
            pos += word_len
            if pinyin_len < 16 and word_len != pinyin_len:  # 部分uwl中拼音最大长度只有8（16字节）
                # 词语有特殊字符，导致长度不同，比如人名中含有字符·－
                logging.debug(f"词语/拼音长度不一致：{word_len}/{pinyin_len}: {' '.join(pinyin_list)} / {word}")
            if word is None:
                continue

            is_error = self._has_invalid_pinyin(pinyin_list) or not valid
            entry = WordEntry(word, pinyin_list, weight, is_error=is_error)
            word_list.append(entry)
        return word_list

    def _decode_word(self, word_data: bytes) -> str | None:
        codes = [self.encoding] + [v for v in ["gbk", "utf-16le", "utf-8"] if v != self.encoding]
        word = None
        try:
            for code in codes:
                word = word_data.decode(code)
                break
        except UnicodeDecodeError:
            pass
        if word is None:  # 第二次尝试，忽略解析错误
            for code in codes:
                word = word_data.decode(code, errors="ignore")
                if word:
                    break
        return word

    def _parse_pinyin(self, data_pinyin: bytes) -> tuple[list[str], bool]:
        step = self.step  # 2字节
        n1 = self.initial_count
        n2 = self.final_count
        valid = True
        pinyin_list = []
        for j in range(0, len(data_pinyin), step):
            sm_raw, ym_raw = data_pinyin[j], data_pinyin[j + 1]  # 声母、韵母
            idx_initial = sm_raw & 0x1F
            idx_final = ((sm_raw >> 5) + (ym_raw << 3)) & 0x1F
            py_initial = self.code_map.get(idx_initial, "*")
            py_final = self.code_map.get(n1 + idx_final, "*")
            pinyin_list.append(py_initial + py_final)
            if idx_initial >= n1 or idx_final >= n2:
                logging.warning(f"拼音索引异常: 声母={idx_initial}, 韵母={idx_final}, {pinyin_list}")
                valid = False

        return pinyin_list, valid

    def _init_encoding(self, data: bytes) -> str:
        # 第3个字节表示字符编码格式: 0x08 是 GBK，0x09 是 UTF-16LE。
        if data[self.struct.encoding_type.start] == 8:
            return "gbk"
        return "utf-16le"
