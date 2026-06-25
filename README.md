# Compressor Lifetime Test System

压缩机寿命耐久测试系统 **Rev 3.2.6** — 基于 NI USB-6362/6363 DAQ 与 PyQt6 的多工位自动化测试平台。

---

## 系统要求

| 项目 | 要求 |
|------|------|
| 操作系统 | Windows 10/11 64-bit |
| Python | 3.10+（源码运行 / 打包） |
| 硬件驱动 | [NI-DAQmx Runtime](https://www.ni.com/en-us/support/downloads/drivers/download.ni-daqmx.html) |
| 采集卡 | NI USB-6362 / 6363 |

---

## 快速开始（源码运行）

```powershell
# 1. 克隆仓库
git clone https://github.com/MichelinZhang/Compressore-Lifetime.git
cd Compressore-Lifetime

# 2. 创建虚拟环境并安装依赖
python -m venv .venv
.\.venv\Scripts\pip install -r requirements-ni.txt

# 3. 启动程序
.\.venv\Scripts\python.exe compressor_lifetime_3_2_6.py
```

---

## 使用手册

### 1. 接线与 IO 位序

每组台架占用 **port 8 路 DO + 1 路 AI**，最多 6 组（Group1~6）：

| line | 0 | 1 | 2 | 3 | 4 | 5 | 6 | 7 |
|------|---|---|---|---|---|---|---|---|
| 功能 | V1 | V2 | V3 | 蜂鸣器 | 压力计供电 | 计数供电 | 计数信号 | 压缩机 |

Group 与端口映射见程序内 `GROUP_MAP`（port0 line0:7 / 8:15 / …，port1 line0:7 / 8:15）。

**联动规则（Rev 3.2.6）：**

- 除复杂脉冲外，**V1 跟随 V3** 电平。
- **复杂脉冲（每轮第 10 次）**：V1/V2 恒低，仅 V3 以 100ms 方波切换；压缩机仍为 1s ON / 1s OFF。

### 2. 界面操作

1. **连接**：选择 Group、填写设备名（默认 `Dev1`），点击「连接」锁定硬件。
2. **参数**：目标循环次数、高压阈值 `target_p`、低压阈值 `floor_p`、保护上限 `max_p`。
3. **开始测试**：启动后按钮变为「暂停测试」。
4. **暂停 / 继续**：手动暂停时压缩机关闭，其余阀门保持；恢复后继续剩余步骤。
5. **停止**：急停，全部 DO 置低。
6. **调试模式**：单工位手动控制 IO，V1/V3 按钮联动。

### 3. 测试流程（单次 Cycle）

```
Phase 1 × 4 轮
  └─ 每轮: 90s 打压/泄压循环 + 57s 泄压 (V2+V3 20s + 静置 37s)

Phase 2 × 14 轮
  └─ 每轮: 10 次脉冲 (9×简单 1s开/关 + 1×复杂) + 57s 泄压

计数器触发 1s → 下一 Cycle
```

### 4. 日志

- CSV 日志保存在主界面设置的日志目录，文件名含设备、Group、port/line、AI 通道与时间戳。
- 字段：Date, Time, Cycle, Phase, Step, End_P, Max_P, Min_P。

### 5. 可调时序常量

在 `compressor_lifetime_3_2_6.py` 顶部：

| 常量 | 默认 | 说明 |
|------|------|------|
| `PULSE_HOLD_S` | 1.0 | 脉冲 ON/OFF 时长 (s) |
| `PULSE_SETTLE_S` | 0.01 | OFF 后切换间隔，MOSFET 可设 0 |
| `COMPLEX_V3_PERIOD_S` | 0.1 | 复杂脉冲 V3 半周期 (s) |
| `RELEASE_V23_S` | 20.0 | 泄压 V2+V3 段 (s) |
| `RELEASE_V1_S` | 37.0 | 泄压静置段 (s) |

---

## 打包发布（Nuitka）

```bat
build.bat
```

或：

```powershell
powershell -ExecutionPolicy Bypass -File scripts\build_nuitka.ps1
```

输出目录：

```
dist\CompressorLifetime\CompressorLifetime.dist\CompressorLifetime.exe
```

**部署注意：**

- 将整份 `CompressorLifetime.dist` 文件夹复制到目标工控机。
- 目标机必须安装 **NI-DAQmx Runtime**。
- 首次构建若无 MSVC，脚本自动使用 MinGW，约需 15–30 分钟。

详见 [BUILD.md](BUILD.md)。

---

## 仓库结构

| 路径 | 说明 |
|------|------|
| `compressor_lifetime_3_2_6.py` | **当前主程序** Rev 3.2.6 |
| `compressor_lifetime_3_*.py` | 历史版本 |
| `compressor_lifetime_4/` | Web 版架构（FastAPI + React，实验性） |
| `python_ni_common/` | 通用 NI 模块 |
| `scripts/build_nuitka.ps1` | Nuitka 打包脚本 |
| `requirements-ni.txt` | Python 依赖 |

---

## 故障排查

| 现象 | 建议 |
|------|------|
| 连接失败 | 确认 DAQmx 已安装、设备名正确、Group 未被其他工位占用 |
| 脉冲中压缩机不动作 | 用示波器看 line7；检查 MOSFET 驱动与供电 |
| 打包失败 | 查看 `nuitka-crash-report.xml`；安装 VS Build Tools 或重试 MinGW |
| 压力读数跳变 | 检查 AI 接线与接地；程序已做中值+滑动平均滤波 |

---

## 版权

Copyright (C) 2026 Fresenius Medical Care. All Rights Reserved.

作者：Zhang zhelei / Michelin
