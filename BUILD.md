# Compressor Lifetime Rev 3.2.7 — 打包说明

## 环境准备

```powershell
cd Compressore-Lifetime
python -m venv .venv
.\.venv\Scripts\pip install -r requirements-ni.txt
```

需要本机已安装 **NI-DAQmx Runtime**（开发与目标机均需）。

## 一键打包

**方式 A — 双击或命令行：**

```bat
build.bat
```

**方式 B — PowerShell：**

```powershell
powershell -ExecutionPolicy Bypass -File scripts\build_nuitka.ps1
```

清理后重新构建：

```powershell
powershell -ExecutionPolicy Bypass -File scripts\build_nuitka.ps1 -Clean
```

## 打包内容

| 文件 | 说明 |
|------|------|
| `compressor_lifetime_3_2_6.py` | 主程序入口 |
| `daq_device_manager.py` | 多工位 DAQ 资源池（共享 ai0:5 + 分组 DO） |

Nuitka 通过 `--include-module=daq_device_manager` 打入 exe 目录，无需单独复制。

## 输出位置

```
dist\CompressorLifetime\CompressorLifetime.dist\
    CompressorLifetime.exe
    (+ 依赖 DLL / Qt 插件等)
```

请将整个 **`CompressorLifetime.dist` 文件夹** 复制到目标工控机，不要只复制单个 exe。

exe 版本信息：**3.2.7**（`file-version` / `product-version`）

## 首次构建说明

- 无 Visual Studio 时脚本自动使用 `--mingw64`，Nuitka 会下载 MinGW（约数百 MB）
- 完整编译约 **15–30 分钟**，请勿中断
- 若失败，查看项目根目录 `nuitka-crash-report.xml`

## 目标机运行

1. 安装 NI-DAQmx Runtime
2. 运行 `CompressorLifetime.exe`
3. 设备名默认 `Dev1`，每台架选择不同 Group（Group1~6）
4. **USB-6363** 支持 6 工位并行；6362 仅支持 Group1~2

## 源码直接运行（开发）

```powershell
.\.venv\Scripts\python.exe compressor_lifetime_3_2_6.py
```

需与 exe 相同目录下存在 `daq_device_manager.py`（已随仓库提供）。
