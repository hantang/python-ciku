"""
百度拼音输入法
- 词库网址: https://shurufa.baidu.com/dict
- 文件后缀: .bdict

词库解析参考
- https://nopdan.com/2022/05/04-baidu-bdict/
- https://github.com/nopdan/rose/blob/main/pkg/pinyin/baidu_bdict.go
- https://github.com/WuLC/ThesaurusParser/blob/master/Baidu/BaiduBdcitReader.java
- https://github.com/Pingze-github/bdictParser/blob/master/bdictParser.py
- https://github.com/studyzy/imewlconverter/blob/master/src/ImeWlConverterCore/IME/BaiduPinyinBdict.cs

范围	描述
特点：词库不带拼音表

解析异常
理工行业/其他/五笔类词库.bdict
电子游戏/网络游戏/魔兽世界-熊猫人.bdict
电子游戏/魔兽世界【熊猫人】.bdict

---

百度手机输入法
- 手机输入法网址 https://mime.baidu.com/web/iw/index/
- 文件后缀: .bcd
- 格式基本相同，但词库描述信息长度不同
"""

import logging
import re
from pathlib import Path

from ..core.base import BaseParser
from ..core.models import DictCell, DictField, DictMeta, DictStruct, WordEntry
from ..core.utils import byte2uint
from ..pinyin.baidu import BAIDU_PINYIN_FINALS as PINYIN_FINALS
from ..pinyin.baidu import BAIDU_PINYIN_INITIALS as PINYIN_INITIALS


class BaiduDictStruct(DictStruct):
    def __init__(self):
        super().__init__(
            count=DictField(start=0x70, end=0x74),
            name=DictField(start=0x90),
            author=DictField(start=0xD0),
            category=DictField(start=0x110),
            description=DictField(start=0x150),
            words=DictField(start=0x350),
        )
        attributes = [
            self.name,
            self.author,
            self.category,
            self.description,
            self.words,
        ]
        self.init_end(attributes)


class BaiduParser(BaseParser):
    suffix = "bdict"
    encoding = "utf-16le"
    struct = BaiduDictStruct()

    initial_count = len(PINYIN_INITIALS)
    final_count = len(PINYIN_FINALS)
    code_map: dict[int, str] = {i: v for i, v in enumerate(PINYIN_INITIALS + PINYIN_FINALS)}

    def parse(self, file_path: Path | str) -> bool:
        self.dict_cell = None
        file_path = Path(file_path)
        self.current_file = file_path.as_posix()
        data = self.read_data(file_path)
        if not self.check(data):
            return False

        start = self.struct.words.start
        word_data = data[start:]
        words = self.extract_words(word_data)

        metadata = self.extract_meta(data)
        metadata.file = file_path.name
        metadata.count_actual = len(words)
        metadata.count_error = sum([1 for w in words if w.is_error])

        self.dict_cell = DictCell(metadata, words)
        return True

    def check(self, data: bytes | None) -> bool:
        if data and data[:8] != b"biptbdsw":
            logging.error(f"文件前缀格式不符合: {self.current_file}")
            return False
        return super().check(data)

    def extract_meta(self, data: bytes) -> DictMeta:
        struct = self.struct
        name = self._decode_text(data, struct.name)
        author = self._decode_text(data, struct.author)
        category = self._decode_text(data, struct.category)
        description = self._decode_text(data, struct.description)
        data_count = byte2uint(data[struct.count.start : struct.count.end])
        metadata = DictMeta(
            name=name,
            author=author,
            category=category,
            description=description,
            count=data_count,
        )

        logging.debug(f"词库 = {name} / 分类 = {category}")
        return metadata

    def extract_words(self, data: bytes, allow_error: bool = False) -> list[WordEntry]:
        step = self.step
        half = step // 2
        word_data = data

        # 存在重复
        word_list = []
        pos = 0
        while pos < len(word_data):
            word_len = byte2uint(word_data[pos : pos + step])
            weight = byte2uint(word_data[pos + step : pos + step * 2])  # bdict基本都是0
            # assert weight == 0
            pos += step * 2

            if word_len == 0:
                word, pinyin_list, pos = self._parse_special(word_data, pos)
                is_error = not word or self._check_pinyin(pinyin_list) or len(word) != pinyin_list
                entry = WordEntry(word, pinyin_list, weight, is_error=is_error)
                word_list.append(entry)  # 备注
                continue

            index1 = byte2uint(word_data[pos : pos + half])
            index2 = byte2uint(word_data[pos + half : pos + step])
            is_error = False

            if self.initial_count <= index1 < 128:
                # 纯英文词语：
                data_pinyin = word_data[pos : pos + word_len]
                pos += word_len
                try:
                    pinyin = data_pinyin.decode("utf-8")
                except UnicodeDecodeError:
                    continue
                word = pinyin
                pinyin_list = [pinyin]  # TODO
            elif index1 == 0 and index2 == 0:
                # 拼音直接编码, 没有分割符，部分长度很大有多余非拼音部分的字符
                pos += step
                word_count = byte2uint(word_data[pos : pos + step])
                pos += step
                data_pinyin = word_data[pos : pos + word_len * 2]
                pos += word_len * 2
                data_word = word_data[pos : pos + word_count * 2]
                pos += word_count * 2
                pinyin = self._decode_data(data_pinyin)
                word = self._decode_data(data_word)
                pinyin_list = [pinyin]
                is_error = True
            else:
                data_pinyin = word_data[pos : pos + word_len * 2]
                pos += word_len * 2
                data_word = word_data[pos : pos + word_len * 2]
                pos += word_len * 2
                pinyin_list = self._parse_pinyin(data_pinyin)
                word = self._decode_data(data_word)
                if (
                    len(word) > 100
                    or len(word) * 5 <= len(pinyin_list)
                    or len(word) > len(pinyin_list)
                ):
                    is_error = True

            is_error = is_error or (not word) or self._check_pinyin(pinyin_list)
            entry = WordEntry(word, pinyin_list, weight, is_error=is_error)  # TODO is_error
            word_list.append(entry)  # 每行：词语 拼音 词频（或权重）

        logging.info(f"word list = {len(word_list)}")
        return word_list

    def _parse_pinyin(self, data_pinyin: bytes) -> list[str]:
        n1 = self.initial_count
        n2 = self.final_count
        step = self.step
        total = len(data_pinyin)

        pinyin_list = []
        for i in range(0, total, step):
            idx_initial = data_pinyin[i]  # 声母
            idx_final = data_pinyin[i + 1] if i + 1 < total else -1  # 韵母

            if 0 <= idx_initial < n1 and 0 <= idx_final < n2:
                py_initial = self.code_map[idx_initial]
                py_final = self.code_map[n1 + idx_final]
                pinyin_list.append(py_initial + py_final)
            else:
                # 直接英文字符
                try:
                    value = self._decode_data(data_pinyin[i : i + step])
                except UnicodeDecodeError:
                    # continue
                    pass
                pinyin_list.append(value)

        return pinyin_list

    def _decode_data(self, data: bytes, strip: bool = True) -> str:
        out = data.decode(self.encoding, errors="ignore")
        out = out.strip(chr(0)) if strip else out
        out = re.sub(r"\s*[\r\n]+\s*", " ", out)
        return out

    def _parse_special(self, word_data: bytes, pos_raw: int) -> tuple[str, list[str], int]:
        """
        TODO 词长、拼音长度为0的
        # zhe'yang'zi'piao'liang'mazheyangzihaonankanye这样子漂亮吗
        """
        step = self.step
        pos = pos_raw

        pinyin_len = byte2uint(word_data[pos : pos + step])
        word_len = byte2uint(word_data[pos + step : pos + step * 2])
        pos += step * 2
        pinyin = self._decode_data(word_data[pos : pos + pinyin_len * 2])
        pos += pinyin_len * 2
        word = self._decode_data(word_data[pos : pos + word_len * 2])
        pos += word_len * 2

        # 额外修正
        pinyin_list = pinyin.split("'")
        word = re.sub(r"[a-zA-Z]+", "", word)
        return word, pinyin_list, pos


class BaiduMobileDictStruct(BaiduDictStruct):
    def __init__(self):
        super().__init__()
        self.suffix = "bcd"  # 后缀不同
        self.description = DictField(start=0x150, end=0x250)  # 词库描述512字节改成256字节


class BaiduMobileParser(BaiduParser):
    suffix = "bcd"
    struct = BaiduMobileDictStruct()
