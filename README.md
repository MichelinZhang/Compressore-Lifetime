# Compressor Lifetime Test System

压缩机寿命耐久测试系统 -- 基于 NI DAQmx 的自动化测试平台

## 简介

本系统用于控制 NI USB-6362/6363 数据采集卡，对压缩机进行全自动的寿命耐久测试。通过精确控制阀门时序、压缩机启停和压力监测，实现多台架并行的循环加压-泄压测试流程。

## 功能特性

- **多台架并行测试** -- 支持动态增删台架，每台架独立控制、独立参数
- **实时压力监测** -- 中值滤波 + 滑动平均双重降噪，实时曲线绘制
- **安全保护机制** -- 压力超限自动停机、紧急停止按钮、脉冲中断安全状态写入
- **调试模式** -- 手动控制 DO 通道，实时查看滤波值与原始值对比
- **仿真模式** -- 无需硬件即可运行全部测试流程
- **自动日志** -- CSV 格式记录每个循环的压力数据（最大值、最小值、结束值）
- **呼吸灯状态指示** -- 运行(绿)、暂停(黄)、故障(红) 动态发光效果

## 技术栈

| 组件 | 技术 |
|------|------|
| GUI 框架 | PyQt6 |
| 实时绘图 | pyqtgraph |
| 硬件驱动 | NI-DAQmx (nidaqmx) |
| 打包工具 | Nuitka |
| 包管理 | uv |
| Python | 3.10+ |

## 快速开始

### 环境准备

```bash
# 安装 uv (如未安装)
pip install uv

# 创建虚拟环境并安装依赖
uv sync
```

### 运行

```bash
# 硬件模式 (需连接 NI USB-6362/6363)
uv run compressor_lifetime/compressor_lifetime_3_1.py

# 仿真模式 (无需硬件)
# 启动后在界面顶部勾选 "仿真模式 (Simulation)"
```

## 硬件连接

| DAQ 通道 | 功能 |
|----------|------|
| port0/line0 | V1 阀门 |
| port0/line1 | V2 阀门 |
| port0/line2 | V3 阀门 |
| port0/line3 | 压缩机 |
| port0/line4 | 压力计供电 |
| port0/line5 | 计数供电 |
| port0/line6 | 计数信号 |
| port0/line7 | 蜂鸣器/报警 |
| ai0 / ai1 ... | 压力传感器 (0-10V, RSE) |

## 测试流程

```
Phase 1: 初始加压 -> 达到目标压力 -> 泄压循环
Phase 2: 30轮脉冲测试 (每轮10次脉冲 + 57s泄压)
计数器触发 -> 进入下一个循环
```

## 项目结构

```
compressor_lifetime/
  compressor_lifetime_3_1.py   # 主程序 (GUI + 测试逻辑)
  pyproject.toml               # 项目配置与依赖
  .python-version              # Python 版本约束
  uv.lock                      # 依赖锁定文件
```

## 版本历史

| 版本 | 变更 |
|------|------|
| Rev 3.2 | UI优化、动画增强、性能提升、鲁棒性修复 |
| Rev 1.0 | 任意删除台架、调试模式增强、中值滤波、暂停修复 |

## 作者

**Zhang Zhelei** -- Fresenius Medical Care / VTC

## 许可

Copyright (C) 2025 Fresenius Medical Care. All Rights Reserved.
