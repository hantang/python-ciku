import logging
import struct
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
    view = memoryview(byte_data)
    size = min(len(view), max_len)
    if byteorder == "little":
        if size == 1:
            return view[0]
        if size == 2:
            return struct.unpack_from("<H", view)[0]
        if size == 4:
            return struct.unpack_from("<I", view)[0]
        if size == 8:
            return struct.unpack_from("<Q", view)[0]
    elif size == 1:
        return view[0]
    elif size == 2:
        return struct.unpack_from(">H", view)[0]
    elif size == 4:
        return struct.unpack_from(">I", view)[0]
    elif size == 8:
        return struct.unpack_from(">Q", view)[0]
    return int.from_bytes(view[:size], byteorder=byteorder)


def byte2str(byte_data: bytes, encoding: str, is_strip: bool = True) -> str:
    try:
        out = byte_data.decode(encoding)
        return out.strip("\x00") if is_strip else out
    except UnicodeDecodeError:
        pass
    return ""
