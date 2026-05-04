# Kindle Manager

Kindle USB 连接电脑后的桌面管理工具，支持书架浏览、笔记导出、词库查询、格式转换。

## 功能

- **书架管理** — 封面网格 / 列表双视图，排序、筛选、搜索、批量操作
- **笔记导出** — 解析 My Clippings.txt，按书分组导出 Markdown / CSV / JSON
- **词库查询** — 读取 vocab.db，按语言过滤，查看单词和语境
- **格式转换** — MOBI/AZW3 → EPUB 内置引擎，安装 Calibre 后支持全格式互转
- **阅读统计** — 格式分布、阅读排行、空间占用

## 使用方式

### 下载打包好的 exe（推荐）

去 [Releases](https://github.com) 页面下载 `KindleManager.exe`，双击运行。

### 从源码运行

```bash
pip install -e .
python -m kindle_manager.main
```

## 依赖

- Python >= 3.10
- PySide6 >= 6.5
- ebooklib >= 0.18
- [Calibre](https://calibre-ebook.com/download)（可选，用于全格式转换）

## 打包

```bash
pyinstaller KindleManager.spec --noconfirm
# 生成 dist/KindleManager.exe
```

## License

MIT
