# Kindle Manager

一个面向 USB 连接 Kindle 的 Windows 桌面管理工具。它可以浏览设备书架、整理阅读笔记、查看生词记录、统计藏书，并调用 Calibre 完成可靠的格式转换。

## 功能

- 书架：封面与列表双视图，支持搜索、筛选、排序和批量操作
- 安全管理：删除书籍时移入设备上的 `.kindle-manager-trash`，不会立即永久删除
- 阅读笔记：解析 `My Clippings.txt`，导出 Markdown、CSV 或 JSON
- 生词本：读取 `vocab.db`，按语言筛选并显示查询语境
- 阅读概览：展示格式分布、空间占用和阅读位置记录
- 格式工具：调用 Calibre 转换 EPUB、MOBI、AZW3、PDF 和 TXT

## 从源码运行

建议使用独立虚拟环境，避免系统中的 Qt DLL 冲突：

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -e .
python -m kindle_manager.main
```

开发与测试：

```powershell
python -m pip install -e ".[dev]"
pytest
ruff check kindle_manager tests
```

## 格式转换

请单独安装 [Calibre](https://calibre-ebook.com/download)。项目不尝试绕过 DRM，也不会使用不完整的二进制提取方式伪造 EPUB。EPUB 不能通过 USB 直接导入 Kindle，可先转换为 AZW3，或使用 Amazon 的 Send to Kindle 服务。

## 打包

```powershell
python -m pip install pyinstaller
pyinstaller KindleManager.spec --noconfirm
```

请在独立虚拟环境中打包。构建配置会排除可能由 Conda `PATH` 注入的旧版 ICU DLL，避免打包后的 QtWidgets 启动失败。

生成文件位于 `dist/KindleManager.exe`。

打包后请运行窗口级冒烟测试；它会区分正常主窗口与 PyInstaller 异常弹窗：

```powershell
powershell -ExecutionPolicy Bypass -File scripts\smoke_test_exe.ps1
```

## 数据恢复

- 删除的书籍位于 Kindle 根目录的 `.kindle-manager-trash` 中。
- 修改 `My Clippings.txt` 前会创建 `My Clippings.txt.bak`。

## License

MIT
