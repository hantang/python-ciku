# Ciku (IME-Utils)

<div align="center">

![GitHub stars](https://img.shields.io/github/stars/hantang/python-ciku?style=flat-square)
![GitHub release](https://img.shields.io/github/v/release/hantang/python-ciku?style=flat-square)
![GitHub repo size](https://img.shields.io/github/repo-size/hantang/python-ciku?style=flat-square)
![GitHub license](https://img.shields.io/github/license/hantang/python-ciku?style=flat-square)

</div>

中文输入法词库文件（细胞词库）解析工具。

> Chinese IME ciku (aka word list / lexicon file) parsing tool.

支持：

- [x] 搜狗拼音（`.scel`）
- [x] 百度拼音（`.bdict`）、百度输入法手机版（`.bcd`）
- [x] QQ 拼音（`.qcel`）、QQ 拼音旧版（6.0 以下词库，`.qpyd`）
- [x] 华宇拼音（紫光输入法）（`.uwl`）

## 使用

- 程序调用：

```python
# 安装
# pip install ciku # ime-utils
# uv pip install -e . # 本地安装（Editable packages）

# 用例：
from ciku import SogouParser, BaiduParser

parser = BaiduParser()
files = [
    "医学词汇.bdict",
    "电影明星.bdict",
    "体操基本术语.bdict",
]

for file in files:
    save_file = f"out-{file}.txt"
    if parser.parse(file):
        parser.save_data(save_file, keep_error=False)
        result = parser.export_data()
```

- 命令行调用

```shell
# 或者 python -m ciku -f file-names -o output

# 指定多个文件
ciku -f file-name1,file-name2 -o output
# 指定目录，-e / --keep-error 保留解析异常词语, -r / --recursive 目录递归检索文件
ciku -d file-dir -o text -e -r
```

## 开发

```shell
# 安装uv <https://docs.astral.sh/uv/>

# 开发环境
uv sync # --dev --all-extras # --locked

# 提交前检查语法等
uvx ruff check .
uvx mypy .

# 构建
uv build
```

## 相关

- [蔷薇词库转换 github-nopdan/rose](https://github.com/nopdan/rose)
- [深蓝词库转换 github-studyzy/imewlconverter](https://github.com/studyzy/imewlconverter)
