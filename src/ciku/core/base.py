import logging
from abc import ABC, abstractmethod
from pathlib import Path

from ..pinyin.syllable import PINYIN_SYLLABLES
from .models import DictCell, DictField, DictMeta, WordEntry
from .utils import byte2str, create_dir


class BaseParser(ABC):
    """
    基类: 输入法细胞词库解析成text文件
    基本流程：
    1. 判断通过文件后缀等判断文件是否符合解析格式
    2. 解析词库词表（如果有）
    3. 解析词语列表
    4. 解析词库元信息并补充额外信息
    """

    suffix: str  # 文件后缀（小写，不带点号）
    encoding: str = "utf-16le"  # 编码类型"utf-16le"最常见

    step: int = 2
    code_map: dict[int, str] = dict()
    dict_cell: DictCell | None = None
    current_file: str = ""
    pinyin_syllables: set[str] = set(PINYIN_SYLLABLES)
    letters: set[str] = set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ")

    @abstractmethod
    def parse(self, file_path: Path | str) -> bool:
        """解析词库文件"""

    def check(self, data: bytes | None) -> bool:
        if not data:
            logging.error(f"{self.current_file} 文件数据为空")
            return False
        return True

    @abstractmethod
    def extract_meta(self, data: bytes) -> DictMeta:
        pass

    @abstractmethod
    def extract_words(self, data: bytes, allow_error: bool = False) -> list[WordEntry]:
        pass

    def _read_data(self, file_path: Path | str) -> bytes:
        file = Path(file_path)
        if not file.exists():
            raise FileExistsError(f"文件 {file} 不存在")

        if file.suffix.lstrip(".").lower() != self.suffix:
            logging.warning(f"后缀不匹配，当前文件后缀 {file.suffix.lower()}, 期望后缀 .{self.suffix}")

        with open(file, "rb") as f:
            return f.read()

    def save_data(
        self,
        save_file: Path | str,
        *,
        keep_error: bool = False,
        meta_comment: str = "#",
        meta_sep: str = " ",
        meta_key_sep: str = ":",
        meta_example_sep: str = "、",
        keep_all_meta: bool = False,
        keep_filename: bool = False,
        field_sep: str = "\t",
        code_sep: str = " ",
        word_first: bool = True,
        keep_weight: bool = True,
    ) -> bool:
        if self.dict_cell is None:
            logging.warning("解析词库列表为空")
            return False

        save_file = Path(save_file)
        logging.debug(f"Save to file {save_file}")
        create_dir(save_file)

        metadata = self.dict_cell.metadata
        words = self.dict_cell.words
        valid_words = [word for word in words if keep_error or not word.is_error]
        logging.debug(f"valid words = {len(valid_words)}")

        meta_str = metadata.to_str(
            comment=meta_comment,
            separator=meta_sep,
            key_sep=meta_key_sep,
            example_sep=meta_example_sep,
            keep_all=keep_all_meta,
            keep_filename=keep_filename,
        )

        word_data = [
            word.to_str(field_sep=field_sep, code_sep=code_sep, word_first=word_first, keep_weight=keep_weight)
            for word in valid_words
        ]
        out_text = "\n".join([meta_str, ""] + word_data)

        with open(save_file, "w", encoding="utf-8") as f:
            f.write(out_text)

        logging.debug("Save done.")
        return True

    def export_data(self, keep_error: bool = False) -> dict[str, list[str]]:
        """导出数据，meta和词库列表"""
        if self.dict_cell is None:
            logging.warning("解析词库列表为空")
            return {"meta": [], "words": []}

        meta_list = self.dict_cell.metadata.to_list()
        word_list = [w.to_str() for w in self.dict_cell.words if keep_error or not w.is_error]
        logging.debug(f"words = {len(word_list)}")

        result = {"meta": meta_list, "words": word_list}
        return result

    def parse_save(
        self,
        file_path: Path | str,
        save_file: Path | str,
        *,
        keep_error: bool = False,
        meta_comment: str = "#",
        meta_sep: str = " ",
        meta_key_sep: str = ":",
        meta_example_sep: str = "、",
        keep_all_meta: bool = False,
        keep_filename: bool = False,
        field_sep: str = "\t",
        code_sep: str = " ",
        word_first: bool = True,
        keep_weight: bool = True,
    ) -> bool:
        if self.parse(file_path):
            return self.save_data(
                save_file,
                keep_error=keep_error,
                meta_comment=meta_comment,
                meta_sep=meta_sep,
                meta_key_sep=meta_key_sep,
                meta_example_sep=meta_example_sep,
                keep_all_meta=keep_all_meta,
                keep_filename=keep_filename,
                field_sep=field_sep,
                code_sep=code_sep,
                word_first=word_first,
                keep_weight=keep_weight,
            )
        return False

    def parse_save_batch(
        self,
        data_dir: Path | str,
        save_dir: Path | str,
        save_suffix: str = ".txt",
        *,
        keep_error: bool = False,
    ):
        if not Path(data_dir).exists():
            logging.info(f"数据目录 = {data_dir} 不存在")
            return
        files = sorted(Path(data_dir).rglob(f"*.{self.suffix}"))
        total_count = len(files)
        logging.info(f"共发现文件 = {total_count}")
        if not files:
            return
        success_count = 0
        for file in files:
            save_file = Path(save_dir, file.relative_to(data_dir)).with_suffix(save_suffix)
            if self.parse(file) and self.save_data(save_file, keep_error=keep_error):
                success_count += 1
        logging.info(f"Process successful = {success_count} / {total_count}")

    def _decode_text(
        self,
        data: bytes,
        offset: DictField | None,
        encoding: str | None = None,
        is_strip: bool = True,
    ) -> str:
        if not encoding:
            encoding = self.encoding
        encode_data = data[offset.start : offset.end] if offset else data
        return byte2str(encode_data, encoding, is_strip)

    def _check_pinyin(self, pinyin_list: list[str], allow_en: bool = True) -> bool:
        """判断拼音需要是否有效
        allow_en允许单个英文字母
        """
        return not all([py in self.pinyin_syllables or (allow_en and py in self.letters) for py in pinyin_list])


class BaseConverter(ABC):
    """
    词库格式转换 # TODO
    """
