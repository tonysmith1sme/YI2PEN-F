# YI2PEN-F DNG 转换器

这是一个专为 **小蚁微单相机 (YI M1)** 用户设计的开源工具。

由于 YI M1 的 RAW (DNG) 文件在 Adobe Lightroom / Camera Raw / DxO PureRAW 等软件中缺乏完善的镜头校正配置文件支持，本工具通过修改 DNG 文件的 EXIF 信息，将其伪装为 **Olympus PEN-F**，从而激活 M43 系统更完善的镜头校正和图像处理支持。

## 下载与使用

**环境要求：**

* Windows 操作系统 (推荐)
* Python 3.6+

**依赖库：**
本项目**仅使用 Python 标准库**，无需 `pip install` 任何第三方包。

**运行步骤：**

```bash
# 1. 克隆仓库
git clone https://github.com/tonysmith1sme/YI2PEN-F.git
cd YI2PEN-F

# 2. 运行脚本
python gui_main.py

```

## 技术细节

* **核心逻辑**：使用 `subprocess` 调用 [ExifTool](https://exiftool.org/) 对 DNG 的元数据进行二进制级别的修改。
* **ExifTool 管理**：
* 脚本包含自动下载器，解析 `exiftool.org/rss.xml` 获取最新版本。
* 自动解压 ZIP 包，智能识别并提取 `exiftool(-k).exe`，重命名并安置在独立的 `ExifTool/` 目录下。


* **GUI 框架**：使用 `tkinter` 标准库，利用 `threading` 实现界面与逻辑分离。

## 📄 许可证与致谢

* 本项目代码基于 MIT License 开源。
* **核心组件致谢**：本项目严重依赖 Phil Harvey 开发的 [ExifTool](https://exiftool.org/)。ExifTool 是一个独立发布的软件，本工具仅提供自动下载和调用功能。

---

**免责声明**：本工具仅修改照片的 EXIF 元数据（制造商和型号），理论上不会影响图像原始数据（Raw Data）。但为了数据安全，建议在使用前备份您的原始照片。