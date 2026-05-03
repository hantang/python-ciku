import argparse
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import TextIO, Type

from .core.base import BaseParser


def show_progress(iterable, prefix: str = "", suffix: str = "", length: int = 50, file: TextIO | None = sys.stderr):
    """A simple progress bar for iterables"""
    count = len(iterable)
    start = time.time()

    def format_time(seconds):
        m, s = divmod(seconds, 60)
        return f"{int(m):02d}:{int(s):02d}"

    for i, item in enumerate(iterable):
        yield item
        elapsed = time.time() - start
        percent = (i + 1) / count
        filled = int(length * percent)
        bar = "█" * filled + " " * (length - filled)
        eta = (elapsed / (i + 1)) * (count - i - 1) if i > 0 else 0
        info = f"\r{prefix} |{bar}| {i + 1}/{count} [{format_time(elapsed)}<{format_time(eta)}, {percent:.1%}] {suffix}"
        print(info, end="", file=file, flush=True)
    print(file=file)  # New line after completion


class ParserFactory:
    """解析器工厂"""

    def __init__(self) -> None:
        self._parsers: dict[str, Type[BaseParser]] = {}

    def register_parser(self, parser_class: Type[BaseParser]) -> None:
        if hasattr(parser_class, "suffix"):
            suffix = parser_class.suffix
            self._parsers[suffix] = parser_class

    def get_parser(self, suffix: str) -> Type[BaseParser]:
        """根据文件获取合适的解析器"""
        suffix = suffix.lstrip(".").lower()
        if suffix in self._parsers:
            return self._parsers[suffix]

        raise ValueError(f"不支持的文件格式: {suffix}")

    def get_suffixes(self) -> list[str]:
        return list(self._parsers.keys())


class ParserToolkit:
    """输入法词库工具：读取并保存"""

    def __init__(self):
        self.factory = ParserFactory()
        self._register_parsers()

    def _register_parsers(self):
        # 动态导入并注册所有解析器
        from ciku import (
            BaiduMobileParser,
            BaiduParser,
            HuayuParser,
            QQParser,
            QQV1Parser,
            SogouParser,
        )

        parsers = [
            SogouParser,
            BaiduParser,
            BaiduMobileParser,
            QQParser,
            QQV1Parser,
            HuayuParser,
        ]
        for parser in parsers:
            self.factory.register_parser(parser)

    def process(self, file_path: Path, save_file: Path, keep_error: bool) -> bool:
        parser = self.get_parser(file_path)
        if parser.parse(file_path):
            return parser.save_data(save_file, keep_error=keep_error)
        return False

    def get_parser(self, file_path: Path) -> BaseParser:
        return self.factory.get_parser(file_path.suffix)()

    @property
    def suffixes(self) -> list[str]:
        return self.factory.get_suffixes()


def run_parallel(todo_files: list[tuple], toolkit: ParserToolkit, keep_error: bool, max_workers: int) -> dict[str, int]:
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {
            executor.submit(toolkit.process, data_file, save_file, keep_error): suffix
            for suffix, data_file, save_file in todo_files
        }
        stats: dict[str, int] = {}
        for future in show_progress(futures.keys(), prefix=f"正在处理（并发度={max_workers}）", suffix="进度"):
            suffix = futures[future]
            if suffix not in stats:
                stats[suffix] = 0
            if future.result():
                stats[suffix] += 1
        return stats


def process(
    file_names: str,
    input_dir: str,
    output_dir: str,
    *,
    workers: int,
    keep_error: bool,
    is_recursive: bool,
    overwrite: bool,
) -> None:
    save_suffix = ".txt"
    toolkit = ParserToolkit()
    suffixes = toolkit.suffixes

    file_items: list[Path] = []
    file_groups: dict[str, list[tuple[Path, Path]]] = {}

    if file_names:
        for name in file_names.split(","):
            file_items.append(Path(name.strip()))
    if input_dir:
        if is_recursive:
            file_items += Path(input_dir).rglob("*.*")
        else:
            file_items += Path(input_dir).glob("*.*")

    print(f"共发现文件 {len(file_items)}")

    # 过滤
    file_ignores: dict[str, int] = {}
    for data_file in file_items:
        suffix = data_file.suffix
        suffix = suffix.lstrip(".").lower()
        if data_file.exists() and suffix in suffixes:
            if suffix not in file_groups:
                file_groups[suffix] = []
                file_ignores[suffix] = 0

            if input_dir:
                data_path = data_file.relative_to(input_dir)
            else:
                data_path = Path(data_file.name)
            save_file = Path(output_dir, data_path).with_suffix(save_suffix)
            if not overwrite and save_file.exists():
                file_ignores[suffix] += 1
            else:
                file_groups[suffix].append((data_file, save_file))

    file_count = sum(map(len, file_groups.values()))
    file_details = ", ".join([f"{k}: {len(v)}" for k, v in file_groups.items()])
    ignore_count = sum(file_ignores.values())
    ignore_details = ", ".join([f"{k}: {v}" for k, v in file_ignores.items()])
    print(f"发现词库文件共 {len(file_items)}")
    print(f"需要处理词库文件 {file_count} （{file_details}）")
    print(f"忽略已存在文件 {ignore_count} （{ignore_details}）")

    if file_count == 0:
        print("没有待处理文件或者后缀格式不支持，请尝试其他文件")
        return

    print(f"解析文件将保存到 {output_dir}")
    print("\n开始处理……")

    stats: dict[str, int] = {}
    start_time = time.time()
    if workers == 1:
        for suffix, file_list in file_groups.items():
            print(f"\n==> 正在处理：词库 = {suffix}")
            stats[suffix] = 0
            for data_file, save_file in show_progress(file_list, f"处理 {suffix:5}", "进度"):
                if toolkit.process(data_file, save_file, keep_error):
                    stats[suffix] += 1
    else:
        all_files = [(k, f1, f2) for k, file_list in file_groups.items() for f1, f2 in file_list]
        print("\n==> 正在处理：所有词库")
        stats = run_parallel(all_files, toolkit, keep_error, workers)

    end_time = time.time()
    elapsed_time = end_time - start_time
    if elapsed_time > 60:
        minutes, seconds = elapsed_time // 60, elapsed_time % 60
        time_log = f"处理时间共: {minutes:02d}: {seconds:.2f}"
    else:
        time_log = f"处理时间共: {elapsed_time:.2f}秒"

    result = "\n".join(
        ["文件类型\t总数 / 成功", "-" * 40]
        + [f"文件（{suffix}）\t{len(file_list):4d} / {stats[suffix]:4d}" for suffix, file_list in file_groups.items()]
        + ["=" * 40, f"结果合计\t{file_count:4d} / {sum(stats.values()):4d}"]
    )
    print(f"\n【处理完成】\n\n{time_log}\n\n{result}\n")


def main() -> int:
    parser = argparse.ArgumentParser(description="输入法词库解析工具")
    parser.add_argument("-f", "--file", type=str, default=None, help="词库文件（逗号分隔多个文件）")
    parser.add_argument("-d", "--dir", type=str, default=None, help="词库目录路径")
    parser.add_argument("-o", "--out", type=str, default=".", help="保存目录路径")
    parser.add_argument("-w", "--workers", type=int, default=1, help="并发处理数")
    parser.add_argument("--keep-error", action="store_true", help="保留解析异常词语")
    parser.add_argument("--recursive", action="store_true", help="词库目录递归检索文件")
    parser.add_argument("--overwrite", action="store_true", help="保存时覆盖已经已存在文件")
    parser.add_argument("--version", action="store_true", help="输出版本信息")

    args = parser.parse_args()
    # print(f"args = {args}")
    if args.version:
        from ciku import __version__

        print(f"当前版本 = {__version__}")
        return 0

    if not args.file and not args.dir:
        parser.print_help()
        print("\n 请配置 -f 指定词库文件，或 -d 指定词库目录")
        return 1

    process(
        args.file,
        args.dir,
        args.out,
        workers=args.workers,
        keep_error=args.keep_error,
        is_recursive=args.recursive,
        overwrite=args.overwrite,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
