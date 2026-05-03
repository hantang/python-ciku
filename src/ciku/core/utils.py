import logging
from pathlib import Path
from typing import Literal


def create_dir(file_path: Path | str, is_dir: bool = False) -> None:
    # 创建文件所在目录
    file_path = Path(file_path)
    dir_path = file_path if is_dir else file_path.parent
    if not dir_path.exists():
        logging.debug(f"Create dir = {dir_path}")
        dir_path.mkdir(parents=True, exist_ok=True)  # 并发可能冲突


def byte2uint(
    byte_data: bytes, byteorder: Literal["little", "big"] = "little", max_len: int = 8
) -> int:
    # N字节编码转换成整数
    return int.from_bytes(byte_data[:max_len], byteorder=byteorder)


def byte2str(byte_data: bytes, encoding: str, is_strip: bool = True) -> str:
    try:
        out = byte_data.decode(encoding)
        return out.strip("\x00") if is_strip else out
    except UnicodeDecodeError:
        pass
    return ""
