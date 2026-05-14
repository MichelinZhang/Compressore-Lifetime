# -*- coding: utf-8 -*-
"""
==============================================================================
项目名称 (Project)   : Compressor Lifetime Test System (压缩机寿命耐久测试系统)
文件名称 (Filename)  : compressor_lifetime_3.1.py
版本号   (Version)   : Rev 3.2
作者     (Author)    : [Zhang zhelei/ Michelin]
所属机构 (Company)   : [Fresenius Medical Care / VTC]
修改日期 (Date)      : 2025-12-17
版权声明 (Copyright) : Copyright (C) 2025 [Fresenius Medical Care]. All Rights Reserved.

功能描述 (Description):
    程序用于控制NI USB-6362/6363数据采集卡，对压缩机进行自动化的寿命测试。
    
    [Rev 1,0修改内容]:
    1. 任意删除：在每个台架卡片右上角增加删除按钮，允许自由移除特定台架。
    2. 调试增强：调试模式 (Debug Mode) 增加实时压力显示功能。
    3. 修改压力传感器代码，提升压力读取的稳定性与准确性。修改为了中值滤波+滑动平均结合的方式。
    4. 暂停功能跳时间了
    5. 保存地址的缓存

    [Rev 3.2修改内容]:
    1. UI优化：统一间距、对齐、圆角，消除错位问题
    2. 动画增强：设置面板展开/收起动画、卡片入场动画、状态切换过渡
    3. 性能优化：使用 deque 替代 list.pop(0) 避免图表刷新卡顿
    4. 鲁棒性提升：异常处理、输入校验、线程安全、资源清理

==============================================================================
"""

# --- 1. 标准库导入 ---
import sys
import os
import time
import random
import csv
import ctypes
import logging
from datetime import datetime
from collections import deque
import statistics

# --- 2. 第三方库导入 (GUI & Plotting) ---
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
                             QHBoxLayout, QGridLayout, QLabel,
                             QLineEdit, QPushButton, QCheckBox, QTextEdit,
                             QFileDialog, QSplitter, QMessageBox,
                             QScrollArea, QDialog, QComboBox,
                             QSizePolicy, QFrame, QGraphicsDropShadowEffect,
                             QGraphicsOpacityEffect)
from PyQt6.QtCore import (Qt, QThread, pyqtSignal, QPropertyAnimation,
                          QEasingCurve, QTimer, QParallelAnimationGroup)
from PyQt6.QtGui import QFont, QColor, QDoubleValidator, QIntValidator

import pyqtgraph as pg

# --- 3. 硬件驱动导入 (NI-DAQmx) ---
import nidaqmx
from nidaqmx.constants import LineGrouping, TerminalConfiguration, AcquisitionType

log = logging.getLogger(__name__)

# ============================================================================
# [SECTION 1] 全局配置与样式 (Global Configuration)
# ============================================================================

IDX_MAP = {
    0: "V1 阀门", 1: "V2 阀门", 2: "V3 阀门", 3: "压缩机",
    4: "压力计供电", 5: "计数供电", 6: "计数信号", 7: "蜂鸣器/报警"
}

SIMULATION_MODE = False

PLOT_MAX_POINTS = 2000

STATUS_STYLES = {
    "run":   "color: #30D158; font-weight: bold; font-size: 14px; background-color: rgba(48,209,88,0.08); border-radius: 6px; padding: 2px 8px;",
    "stop":  "color: #8E8E93; font-weight: bold; font-size: 14px; background-color: rgba(142,142,147,0.08); border-radius: 6px; padding: 2px 8px;",
    "err":   "color: #FF453A; font-weight: bold; font-size: 14px; background-color: rgba(255,69,58,0.08); border-radius: 6px; padding: 2px 8px;",
    "pause": "color: #FF9F0A; font-weight: bold; font-size: 14px; background-color: rgba(255,159,10,0.08); border-radius: 6px; padding: 2px 8px;",
}

IOS_LIGHT_THEME = """
    QWidget {
        background-color: #F9F9F9; color: #1C1C1E;
        font-family: "Segoe UI Variable", "Segoe UI", "Microsoft YaHei UI", sans-serif;
        font-size: 13px;
    }
    QMainWindow, QWidget#CentralWidget { background-color: #F2F2F7; }

    QFrame#SettingsPanel {
        background-color: #FFFFFF;
        border-bottom: 1px solid #E5E5EA;
    }
    QFrame#Card {
        background-color: #FFFFFF;
        border-radius: 18px;
        border: 1px solid rgba(0,0,0,0.06);
    }

    QLabel#CardTitle {
        font-size: 17px; font-weight: 700; color: #1C1C1E;
        background-color: transparent; letter-spacing: -0.4px;
    }
    QLabel { background-color: transparent; color: #1C1C1E; }
    QLabel.SubLabel { font-size: 11px; color: #8E8E93; letter-spacing: 0.3px; }

    QLineEdit, QComboBox {
        background-color: #F2F2F7; border: 1px solid #E5E5EA; border-radius: 10px;
        padding: 7px 12px; color: #000000; font-size: 13px;
        selection-background-color: #007AFF;
    }
    QLineEdit:focus { border: 2px solid #007AFF; background-color: #FFFFFF; padding: 6px 11px; }
    QLineEdit:disabled { background-color: #E8E8ED; color: #8E8E93; }
    QComboBox::drop-down { border: none; width: 24px; }
    QComboBox::down-arrow { image: none; border: none; }
    QComboBox QAbstractItemView {
        background-color: #FFFFFF; border: 1px solid #E5E5EA;
        border-radius: 10px; padding: 4px; selection-background-color: #007AFF;
    }

    QPushButton {
        border-radius: 10px; padding: 8px 18px;
        font-weight: 600; font-size: 13px;
    }
    QPushButton#BtnPrimary { background-color: #007AFF; color: white; border: none; }
    QPushButton#BtnPrimary:hover { background-color: #0062CC; }
    QPushButton#BtnPrimary:pressed { background-color: #004EA3; }
    QPushButton#BtnPrimary:disabled { background-color: #B4D9FF; color: rgba(255,255,255,0.7); }

    QPushButton#BtnSuccess { background-color: #30D158; color: white; border: none; }
    QPushButton#BtnSuccess:hover { background-color: #28B74C; }

    QPushButton#BtnSecondary { background-color: #FFFFFF; color: #007AFF; border: 1px solid #D1D1D6; }
    QPushButton#BtnSecondary:hover { background-color: #F2F2F7; }
    QPushButton#BtnSecondary:pressed { background-color: #E8E8ED; }

    QPushButton#BtnDanger { background-color: #FF453A; color: white; border: none; }
    QPushButton#BtnDanger:hover { background-color: #D63027; }
    QPushButton#BtnDanger:pressed { background-color: #B22A22; }
    QPushButton#BtnDanger:disabled { background-color: #FFB2AC; color: rgba(255,255,255,0.7); }

    QPushButton#BtnAdd {
        background-color: #F0FFF4; color: #30D158;
        border: 1.5px solid #30D158; font-weight: 700;
    }
    QPushButton#BtnAdd:hover { background-color: #D4F5DF; }

    QPushButton#BtnDeleteCard {
        background-color: transparent; color: #C7C7CC; border: none;
        font-weight: bold; font-size: 16px; padding: 0px;
    }
    QPushButton#BtnDeleteCard:hover {
        color: #FF453A; background-color: rgba(255,69,58,0.08); border-radius: 15px;
    }

    QPushButton#BtnToggleSettings {
        background-color: transparent; color: #8E8E93; border: none;
        font-weight: 600; text-align: left; padding-left: 20px;
        font-size: 12px; letter-spacing: 0.3px;
    }
    QPushButton#BtnToggleSettings:hover { color: #007AFF; }

    QScrollArea { border: none; background-color: transparent; }
    QWidget#ScrollContents { background-color: transparent; }
    QSplitter::handle { background-color: #E5E5EA; margin: 0px; border-radius: 2px; }
    QSplitter::handle:hover { background-color: #007AFF; }
    QTextEdit {
        background-color: #FAFAFA; color: #333333; border-radius: 10px;
        font-family: "Cascadia Code", "Consolas", "Menlo", monospace;
        font-size: 12px; border: 1px solid #E5E5EA; padding: 8px;
        selection-background-color: #007AFF;
    }
    QDialog { background-color: #FFFFFF; border-radius: 16px; }
    QCheckBox { spacing: 6px; }
    QCheckBox::indicator {
        width: 18px; height: 18px; border-radius: 4px;
        border: 2px solid #C7C7CC;
    }
    QCheckBox::indicator:checked { background-color: #007AFF; border-color: #007AFF; }
"""


# ============================================================================
# [SECTION 2] 系统工具函数 (System Utilities)
# ============================================================================

def set_keep_awake(enable=True):
    try:
        ES_CONTINUOUS = 0x80000000
        ES_SYSTEM_REQUIRED = 0x00000001
        ES_DISPLAY_REQUIRED = 0x00000002
        if enable:
            ctypes.windll.kernel32.SetThreadExecutionState(
                ES_CONTINUOUS | ES_SYSTEM_REQUIRED | ES_DISPLAY_REQUIRED)
        else:
            ctypes.windll.kernel32.SetThreadExecutionState(ES_CONTINUOUS)
    except Exception:
        log.warning("SetThreadExecutionState 调用失败", exc_info=True)


def validate_positive_float(text, field_name, min_val=0.0, max_val=99.9):
    try:
        val = float(text)
    except (ValueError, TypeError):
        raise ValueError(f"{field_name} 必须为有效数字")
    if val < min_val or val > max_val:
        raise ValueError(f"{field_name} 超出有效范围 [{min_val}, {max_val}]")
    return val


def validate_positive_int(text, field_name, min_val=1, max_val=999999):
    try:
        val = int(text)
    except (ValueError, TypeError):
        raise ValueError(f"{field_name} 必须为正整数")
    if val < min_val or val > max_val:
        raise ValueError(f"{field_name} 超出有效范围 [{min_val}, {max_val}]")
    return val


# ============================================================================
# [SECTION 3] 核心逻辑层 (Core Logic / Backend)
# ============================================================================

class RetryCycleError(Exception):
    pass


class TestWorker(QThread):
    sig_log = pyqtSignal(str)
    sig_pressure = pyqtSignal(float)
    sig_status = pyqtSignal(str, str)
    sig_progress = pyqtSignal(int)
    sig_finished = pyqtSignal()
    sig_error = pyqtSignal(str)
    sig_timer = pyqtSignal(str)
    sig_button_update = pyqtSignal(str)
    sig_result = pyqtSignal(bool)  # True = success, False = error/stopped

    def __init__(self, config, group_offset, log_dir):
        super().__init__()
        self.config = config
        self.offset = group_offset
        self.log_dir = log_dir
        self.is_running = True
        self.is_paused = False
        self.do_task = None
        self.ai_task = None
        self.csv_file = None
        self.dev_name = config['device']
        self.target_cycles = int(config['cycles'])
        self.target_p = float(config['target_p'])
        self.floor_p = float(config['floor_p'])
        self.max_p = float(config['max_p'])
        self.sim_mode = config['simulation']
        self._sim_p_val = 0.0
        self._last_pressure = 0.0
        self._first_read = True
        self.pressure_deque = deque(maxlen=4)
        self.step_max_p = 0.0
        self.step_min_p = 99.9
        self.fault_triggered = False
        self.last_do_states = [False] * 8
        self._needs_emergency_shutdown = False

    def run(self):
        try:
            self.setup_hardware()
            self.create_log_file()
            self.sig_log.emit(f"启动: {self.dev_name} [Line {self.offset}-{self.offset+7}]")

            current_cycle = 1
            while current_cycle <= self.target_cycles:
                if not self.is_running:
                    break

                try:
                    self.check_pause_state()
                    self.sig_status.emit(f"循环 {current_cycle}: 启动", STATUS_STYLES["run"])

                    if not self.run_phase_1(current_cycle):
                        if not self.is_running:
                            break

                    if not self.run_phase_2(current_cycle):
                        if not self.is_running:
                            break

                    self.sig_status.emit(f"循环 {current_cycle}: 计数器触发", STATUS_STYLES["run"])
                    self._trigger_counter()

                    if not self.sleep_smart(1.0):
                        break

                    self.sig_progress.emit(current_cycle)
                    current_cycle += 1

                except RetryCycleError:
                    if not self.is_running:
                        break
                    self.sig_log.emit(f"警告: 第 {current_cycle} 次循环发生故障，系统复位并重跑当前循环...")
                    self.sig_status.emit(f"正在复位循环 {current_cycle}...", STATUS_STYLES["run"])
                    self.finalize_success()
                    time.sleep(2.0)
                    continue

            if self.is_running:
                self.finalize_success()
                self.sig_status.emit("测试完成", STATUS_STYLES["run"])
                self.sig_log.emit(f"{self.dev_name}: 测试流程已顺利完成")
                self.sig_timer.emit("--")
                self.sig_result.emit(True)
            else:
                self.sig_status.emit("已停止", STATUS_STYLES["err"])
                self.sig_result.emit(False)

        except Exception as e:
            self.sig_error.emit(f"系统异常: {e}")
            log.exception("TestWorker 运行异常")
            self.emergency_shutdown()
            self.sig_result.emit(False)
        finally:
            self.cleanup()
            self.sig_finished.emit()

    def check_pause_state(self):
        if self.is_paused and self.is_running:
            self.sig_status.emit("已暂停 / 等待恢复", STATUS_STYLES["pause"])
            temp_safe_states = list(self.last_do_states)
            temp_safe_states[3] = False
            if self.fault_triggered:
                temp_safe_states[7] = True
                self.sig_log.emit("故障暂停: 等待用户操作 (复位模式)")
            else:
                self.sig_log.emit("手动暂停: 保持状态 (继续模式)")

            if not self.sim_mode and self.do_task:
                try:
                    self.do_task.write(temp_safe_states)
                except nidaqmx.DaqError as e:
                    log.warning("暂停时写入DO失败: %s", e)

            while self.is_paused and self.is_running:
                time.sleep(0.1)
                self.read_pressure(silent=True)

            if self.is_running:
                if self.fault_triggered:
                    self.fault_triggered = False
                    raise RetryCycleError()
                else:
                    self.sig_status.emit("恢复运行...", STATUS_STYLES["run"])
                    self.sig_log.emit("手动暂停结束，继续执行剩余步骤")
                    self.write_do(self.last_do_states)

    def trigger_fault(self, error_msg):
        self.fault_triggered = True
        self.is_paused = True
        self.sig_error.emit(error_msg)
        self.sig_button_update.emit("continue")
        self.check_pause_state()

    def set_pause(self, paused):
        self.is_paused = paused

    def stop(self):
        self.is_running = False
        self.is_paused = False
        self.sig_log.emit("!!! 用户触发紧急停止 !!!")
        self.sig_status.emit("正在停止...", STATUS_STYLES["err"])
        self._needs_emergency_shutdown = True

    def setup_hardware(self):
        if self.sim_mode:
            return
        lines = f"{self.dev_name}/port0/line{self.offset}:{self.offset+7}"
        self.do_task = nidaqmx.Task()
        try:
            self.do_task.do_channels.add_do_chan(
                lines, line_grouping=LineGrouping.CHAN_PER_LINE)
            self.do_task.start()
            self.do_task.write([False] * 8)
        except Exception as e:
            self.do_task.close()
            self.do_task = None
            raise RuntimeError(f"DO初始化失败: {e}") from e

        ai_idx = self.offset // 8
        ai_chan = f"{self.dev_name}/ai{ai_idx}"
        self.ai_task = nidaqmx.Task()
        try:
            self.ai_task.ai_channels.add_ai_voltage_chan(
                ai_chan, terminal_config=TerminalConfiguration.RSE,
                min_val=-10.0, max_val=10.0)
            self.ai_task.timing.cfg_samp_clk_timing(
                rate=500, sample_mode=AcquisitionType.CONTINUOUS,
                samps_per_chan=1000)
            self.ai_task.start()
        except Exception as e:
            self.ai_task.close()
            self.ai_task = None
            if self.do_task:
                self.do_task.close()
                self.do_task = None
            raise RuntimeError(f"AI初始化失败: {e}") from e

    def read_pressure(self, silent=False):
        if self.sim_mode:
            return self._simulate_pressure(silent)

        try:
            data = self.ai_task.read(
                number_of_samples_per_channel=nidaqmx.constants.READ_ALL_AVAILABLE)

            if len(data) == 0:
                return self._last_pressure

            if len(data) >= 3:
                current_volts = statistics.median(data)
            else:
                current_volts = data[0]

            current_p = max(0, (current_volts - 1.0) * 2.5)

            self.pressure_deque.append(current_p)

            filtered_p = sum(self.pressure_deque) / len(self.pressure_deque)
            if filtered_p < 0.015:
                filtered_p = 0.0

            self._last_pressure = filtered_p

            if not silent:
                self.sig_pressure.emit(filtered_p)

            self._update_stats(filtered_p)
            self._check_safety(filtered_p)
            return filtered_p

        except Exception as e:
            if self.is_running:
                raise
            return 0.0

    def write_do(self, states):
        if not self.is_running:
            return
        self.last_do_states = list(states)

        if self.sim_mode:
            return self._simulate_response(states)
        if self.do_task:
            try:
                self.do_task.write(states)
            except nidaqmx.DaqError as e:
                self.is_running = False
                self.sig_error.emit(f"写入硬件失败: {e}")

    def emergency_shutdown(self):
        if self.sim_mode:
            return
        if self.do_task:
            try:
                self.do_task.stop()
                self.do_task.start()
                self.do_task.write([False] * 8)
            except Exception:
                log.warning("紧急关闭时写入DO失败", exc_info=True)

    def run_phase_1(self, cycle):
        success_count = 0
        for i in range(1):
            self.check_pause_state()
            self.step_max_p = 0.0
            self.step_min_p = 99.9
            if not self.is_running:
                return False
            self.sig_status.emit(f"P1 ({i+1}/1): 初始加压", STATUS_STYLES["run"])
            current_loop_reached = False
            in_release_mode = False
            t_start = time.time()
            while time.time() - t_start < 90.0:
                if not self.is_running:
                    return False

                if self.is_paused:
                    self.check_pause_state()

                self.sig_timer.emit(f"{90.0 - (time.time() - t_start):.1f}")
                p = self.read_pressure()
                states = [False] * 8
                states[0] = True
                states[4] = True
                states[5] = True
                if not in_release_mode:
                    states[3] = True
                    if p >= self.target_p:
                        current_loop_reached = True
                        in_release_mode = True
                        states[3] = True
                        states[1] = True
                        states[2] = True
                        states[0] = False
                        self.sig_status.emit(f"P1 ({i+1}/1): 达标泄压", STATUS_STYLES["run"])
                else:
                    states[3] = True
                    states[1] = True
                    states[2] = True
                    states[0] = False
                    if p <= self.floor_p:
                        in_release_mode = False
                        self.sig_status.emit(f"P1 ({i+1}/1): 重新打压", STATUS_STYLES["run"])
                self.write_do(states)
                time.sleep(0.1)
            if current_loop_reached:
                success_count += 1
            else:
                self.sig_log.emit(f"警告: P1 第 {i+1} 次循环未达到目标压力")
            if not self.run_release_57s(cycle, f"P1 ({i+1}/1)"):
                return False
            self.log_csv(cycle, "Phase_1", f"{i+1}/1 Done", self.read_pressure(silent=True))
        if success_count == 0:
            self.trigger_fault(f"故障: 阶段一循环均未达到目标压力 {self.target_p} Bar")
            return False
        return True

    def run_phase_2(self, cycle):
        total_rounds = 30
        for i in range(total_rounds):
            self.check_pause_state()
            self.step_max_p = 0.0
            self.step_min_p = 99.9
            if not self.is_running:
                return False
            for j in range(10):
                if not self.is_running:
                    return False
                if self.is_paused:
                    self.check_pause_state()

                self.sig_status.emit(
                    f"P2 ({i+1}/{total_rounds}): 脉冲 {j+1}/10", STATUS_STYLES["run"])
                if j == 9:
                    self._run_complex_pulse()
                else:
                    self._run_simple_pulse()
            if not self.run_release_57s(cycle, f"P2 ({i+1}/{total_rounds})"):
                return False
            self.log_csv(cycle, "Phase_2", f"{i+1}/{total_rounds} Done",
                         self.read_pressure(silent=True))
        return True

    def run_release_57s(self, cycle, phase_name):
        self.sig_status.emit(f"{phase_name}: 泄压 (V2+V3)", STATUS_STYLES["run"])
        s_a = [False] * 8
        s_a[1] = True
        s_a[2] = True
        s_a[4] = True
        s_a[5] = True
        self.write_do(s_a)
        if not self.sleep_smart(20.0):
            return False
        self.sig_status.emit(f"{phase_name}: 泄压 (V1)", STATUS_STYLES["run"])
        s_b = [False] * 8
        s_b[0] = True
        s_b[4] = True
        s_b[5] = True
        self.write_do(s_b)
        if not self.sleep_smart(37.0):
            return False
        return True

    def sleep_smart(self, duration):
        start = time.time()
        while time.time() - start < duration:
            if not self.is_running:
                return False
            if self.is_paused:
                self.check_pause_state()
            self.sig_timer.emit(f"{duration - (time.time() - start):.1f}")
            self.read_pressure()
            time.sleep(0.1)
        self.sig_timer.emit("0.0")
        return True

    def finalize_success(self):
        if self.sim_mode:
            return
        if self.do_task:
            try:
                f = [False] * 8
                f[4] = True
                f[5] = True
                self.do_task.write(f)
            except Exception:
                log.warning("finalize_success 写入DO失败", exc_info=True)

    def cleanup(self):
        if self._needs_emergency_shutdown:
            self.emergency_shutdown()
            self._needs_emergency_shutdown = False

        if not self.sim_mode and self.do_task:
            try:
                states = [False] * 8
                if self.fault_triggered:
                    states[7] = True
                self.do_task.write(states)
                self.do_task.close()
            except Exception:
                log.warning("cleanup DO 关闭失败", exc_info=True)
            finally:
                self.do_task = None
        if not self.sim_mode and self.ai_task:
            try:
                self.ai_task.close()
            except Exception:
                log.warning("cleanup AI 关闭失败", exc_info=True)
            finally:
                self.ai_task = None

    def create_log_file(self):
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.csv_file = os.path.join(
            self.log_dir, f"Log_{self.dev_name}_Grp{self.offset//8}_{ts}.csv")
        with open(self.csv_file, 'w', newline='', encoding='utf-8') as f:
            csv.writer(f).writerow(
                ["Date", "Time", "Cycle", "Phase", "Step", "End_P", "Max_P", "Min_P"])

    def log_csv(self, cycle, phase, step, end_p):
        if not self.csv_file:
            return
        try:
            n = datetime.now()
            with open(self.csv_file, 'a', newline='', encoding='utf-8') as f:
                csv.writer(f).writerow([
                    n.strftime("%Y-%m-%d"), n.strftime("%H:%M:%S"),
                    cycle, phase, step, f"{end_p:.2f}",
                    f"{self.step_max_p:.2f}", f"{self.step_min_p:.2f}"])
        except OSError as e:
            log.warning("CSV 写入失败: %s", e)

    def _simulate_pressure(self, silent):
        time.sleep(0.02)
        noise = random.uniform(-0.05, 0.05)
        self._sim_p_val = max(0, self._sim_p_val + noise)
        if not silent:
            self.sig_pressure.emit(self._sim_p_val)
        self._update_stats(self._sim_p_val)
        self._check_safety(self._sim_p_val)
        return self._sim_p_val

    def _simulate_response(self, states):
        if states[3] and states[0]:
            self._sim_p_val += 0.15
        elif states[1] or states[2]:
            self._sim_p_val = max(0, self._sim_p_val - 0.3)
        elif states[0]:
            self._sim_p_val = max(0, self._sim_p_val - 0.05)

    def _update_stats(self, val):
        if val > self.step_max_p:
            self.step_max_p = val
        if val < self.step_min_p:
            self.step_min_p = val

    def _check_safety(self, val):
        if val > self.max_p:
            self.trigger_fault(f"压力超限: {val:.2f} > {self.max_p}")

    def _trigger_counter(self):
        s = [False] * 8
        s[1] = True
        s[2] = True
        s[4] = True
        s[5] = True
        s[6] = True
        self.write_do(s)

    def _write_safe_idle(self):
        safe = [False] * 8
        safe[4] = True
        safe[5] = True
        self.write_do(safe)

    def _run_simple_pulse(self):
        s_on = [False] * 8
        s_on[0] = True
        s_on[3] = True
        s_on[4] = True
        s_on[5] = True
        self.write_do(s_on)
        if not self.sleep_smart(1.0):
            self._write_safe_idle()
            return
        s_off = [False] * 8
        s_off[0] = True
        s_off[4] = True
        s_off[5] = True
        self.write_do(s_off)
        if not self.sleep_smart(1.0):
            self._write_safe_idle()
            return

    def _run_complex_pulse(self):
        for _ in range(5):
            if not self.is_running:
                self._write_safe_idle()
                return
            s1 = [False] * 8
            s1[0] = True
            s1[3] = True
            s1[2] = True
            s1[4] = True
            s1[5] = True
            self.write_do(s1)
            if not self.sleep_smart(0.1):
                self._write_safe_idle()
                return
            s2 = [False] * 8
            s2[0] = True
            s2[3] = True
            s2[4] = True
            s2[5] = True
            self.write_do(s2)
            if not self.sleep_smart(0.1):
                self._write_safe_idle()
                return
        for _ in range(5):
            if not self.is_running:
                self._write_safe_idle()
                return
            s3 = [False] * 8
            s3[0] = True
            s3[2] = True
            s3[4] = True
            s3[5] = True
            self.write_do(s3)
            if not self.sleep_smart(0.1):
                self._write_safe_idle()
                return
            s4 = [False] * 8
            s4[0] = True
            s4[4] = True
            s4[5] = True
            self.write_do(s4)
            if not self.sleep_smart(0.1):
                self._write_safe_idle()
                return


# ============================================================================
# [SECTION 4] 辅助 UI 组件 (Dialogs)
# ============================================================================

class ManualControlDialog(QDialog):
    def __init__(self, dev_name, offset, station_widget, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"调试模式 (Debug) – {dev_name}")
        self.setFixedSize(480, 660)
        self.dev_name = dev_name
        self.offset = offset
        self.station = station_widget
        self.do_task = None
        self.ai_task = None
        self.current_states = [False] * 8
        self.buttons = []
        self._sim_p = 0.0
        self.debug_deque = deque(maxlen=4)
        self.init_ui()
        self.start_tasks()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(24, 24, 24, 24)

        title = QLabel(f"IO Control: Line {self.offset} – {self.offset+7}")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet(
            "font-size: 16px; font-weight: 700; color: #1C1C1E; letter-spacing: -0.3px;")
        layout.addWidget(title)

        p_frame = QFrame()
        p_frame.setStyleSheet(
            "background-color: #F2F2F7; border-radius: 12px; "
            "border: 1px solid rgba(0,0,0,0.06);")
        p_lay = QVBoxLayout(p_frame)
        p_lay.setSpacing(4)
        p_lay.setContentsMargins(16, 12, 16, 12)

        row1 = QHBoxLayout()
        lbl_filt_title = QLabel("算法滤波值")
        lbl_filt_title.setStyleSheet("color: #8E8E93; font-size: 11px; letter-spacing: 0.3px;")
        row1.addWidget(lbl_filt_title)
        self.lbl_filtered_p = QLabel("0.00 Bar")
        self.lbl_filtered_p.setStyleSheet("font-size: 24px; font-weight: 700; color: #007AFF;")
        self.lbl_filtered_p.setAlignment(Qt.AlignmentFlag.AlignRight)
        row1.addWidget(self.lbl_filtered_p)

        sep = QFrame()
        sep.setFixedHeight(1)
        sep.setStyleSheet("background-color: #E5E5EA;")

        row2 = QHBoxLayout()
        lbl_raw_title = QLabel("原始瞬时值 (Raw)")
        lbl_raw_title.setStyleSheet("color: #8E8E93; font-size: 11px; letter-spacing: 0.3px;")
        row2.addWidget(lbl_raw_title)
        self.lbl_raw_p = QLabel("0.00 Bar")
        self.lbl_raw_p.setStyleSheet("font-size: 13px; font-weight: 600; color: #FF453A;")
        self.lbl_raw_p.setAlignment(Qt.AlignmentFlag.AlignRight)
        row2.addWidget(self.lbl_raw_p)

        p_lay.addLayout(row1)
        p_lay.addWidget(sep)
        p_lay.addLayout(row2)
        layout.addWidget(p_frame)

        grid = QGridLayout()
        grid.setSpacing(8)
        grid.setContentsMargins(0, 4, 0, 4)
        for i in range(8):
            name = IDX_MAP.get(i, f"Line {i}")
            btn = QPushButton(f"{name}\nOFF")
            btn.setCheckable(True)
            btn.setFixedHeight(56)
            btn.setStyleSheet(
                "background-color: #F2F2F7; color: #8E8E93; "
                "border: 1px solid #E5E5EA; border-radius: 10px; "
                "font-size: 12px; font-weight: 600;")
            btn.clicked.connect(lambda chk, idx=i: self.toggle_line(idx))
            grid.addWidget(btn, i // 2, i % 2)
            self.buttons.append(btn)
        layout.addLayout(grid)

        line = QFrame()
        line.setFixedHeight(1)
        line.setStyleSheet("background-color: #E5E5EA;")
        layout.addWidget(line)

        lbl_ui = QLabel("运行状态测试")
        lbl_ui.setStyleSheet(
            "font-weight: 600; color: #8E8E93; font-size: 11px; letter-spacing: 0.3px;")
        layout.addWidget(lbl_ui)

        ui_box = QHBoxLayout()
        ui_box.setSpacing(8)
        state_btns = [
            ("运行", "#30D158", lambda: self.station.set_glow_state("run")),
            ("报警", "#FF453A", self.manual_trigger_alarm),
            ("暂停", "#FF9F0A", lambda: self.station.set_glow_state("pause")),
            ("待机", "#8E8E93", lambda: self.station.set_glow_state("idle")),
        ]
        for text, color, handler in state_btns:
            btn = QPushButton(text)
            btn.setFixedHeight(36)
            btn.setStyleSheet(
                f"background-color: {color}; color: white; border: none; "
                f"border-radius: 8px; font-weight: 600; font-size: 12px;")
            btn.clicked.connect(handler)
            ui_box.addWidget(btn)
        layout.addLayout(ui_box)
        layout.addStretch()

        close_btn = QPushButton("断开连接并关闭")
        close_btn.setObjectName("BtnPrimary")
        close_btn.setFixedHeight(40)
        close_btn.clicked.connect(self.accept)
        layout.addWidget(close_btn)

    def start_tasks(self):
        if not SIMULATION_MODE:
            try:
                self.do_task = nidaqmx.Task()
                lines = f"{self.dev_name}/port0/line{self.offset}:{self.offset+7}"
                self.do_task.do_channels.add_do_chan(
                    lines, line_grouping=LineGrouping.CHAN_PER_LINE)
                self.do_task.start()
                self.do_task.write([False] * 8)
            except Exception as e:
                QMessageBox.critical(self, "硬件错误 (DO)", f"无法占用DO通道:\n{e}")
                self.do_task = None

            try:
                self.ai_task = nidaqmx.Task()
                ai_idx = self.offset // 8
                ai_chan = f"{self.dev_name}/ai{ai_idx}"
                self.ai_task.ai_channels.add_ai_voltage_chan(
                    ai_chan, terminal_config=TerminalConfiguration.RSE,
                    min_val=-10.0, max_val=10.0)
                self.ai_task.timing.cfg_samp_clk_timing(
                    rate=500, sample_mode=AcquisitionType.CONTINUOUS,
                    samps_per_chan=1000)
                self.ai_task.start()
            except Exception as e:
                log.warning("AI Task 初始化失败 (调试模式): %s", e)
                if self.ai_task:
                    try:
                        self.ai_task.close()
                    except Exception:
                        pass
                self.ai_task = None

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_pressure)
        self.timer.start(100)

    def update_pressure(self):
        raw_val = 0.0
        filtered_val = 0.0

        if SIMULATION_MODE:
            if self.current_states[3] and self.current_states[0]:
                self._sim_p += 0.2
            elif self.current_states[1] or self.current_states[2]:
                self._sim_p -= 0.3
            else:
                self._sim_p -= 0.05
            base_p = max(0, min(3.0, self._sim_p))

            noise = random.uniform(-0.15, 0.15)
            raw_val = max(0, base_p + noise)
            self.debug_deque.append(raw_val)
            filtered_val = sum(self.debug_deque) / len(self.debug_deque)

        elif self.ai_task:
            try:
                data = self.ai_task.read(
                    number_of_samples_per_channel=nidaqmx.constants.READ_ALL_AVAILABLE)

                if len(data) > 0:
                    raw_volts = data[-1]
                    raw_val = max(0, (raw_volts - 1.0) * 2.5)

                    if len(data) >= 3:
                        median_volts = statistics.median(data)
                    else:
                        median_volts = sum(data) / len(data)

                    mid_p = max(0, (median_volts - 1.0) * 2.5)
                    self.debug_deque.append(mid_p)
                    filtered_val = sum(self.debug_deque) / len(self.debug_deque)
                    if filtered_val < 0.05:
                        filtered_val = 0.0
                else:
                    if self.debug_deque:
                        filtered_val = self.debug_deque[-1]

            except Exception:
                raw_val = 0.0
                filtered_val = 0.0

        self.lbl_filtered_p.setText(f"{filtered_val:.2f} Bar")
        self.lbl_raw_p.setText(f"{raw_val:.2f} Bar")

    def manual_trigger_alarm(self):
        self.station.set_glow_state("error")
        if not SIMULATION_MODE and self.do_task:
            try:
                states = [False] * 8
                states[7] = True
                self.do_task.write(states)
                for i, btn in enumerate(self.buttons):
                    btn.setChecked(i == 7)
                    self.update_btn_style(i, i == 7)
            except Exception as e:
                QMessageBox.warning(self, "错误", f"硬件写入失败: {e}")

    def toggle_line(self, idx):
        is_on = self.buttons[idx].isChecked()
        self.current_states[idx] = is_on
        self.update_btn_style(idx, is_on)
        if not SIMULATION_MODE and self.do_task:
            try:
                self.do_task.write(self.current_states)
            except nidaqmx.DaqError as e:
                log.warning("调试模式DO写入失败: %s", e)

    def update_btn_style(self, idx, is_on):
        btn = self.buttons[idx]
        name = IDX_MAP.get(idx)
        if is_on:
            btn.setText(f"{name}\nON")
            btn.setStyleSheet(
                "background-color: #30D158; color: white; border: none; "
                "border-radius: 10px; font-size: 12px; font-weight: 600;")
        else:
            btn.setText(f"{name}\nOFF")
            btn.setStyleSheet(
                "background-color: #F2F2F7; color: #8E8E93; "
                "border: 1px solid #E5E5EA; border-radius: 10px; "
                "font-size: 12px; font-weight: 600;")

    def closeEvent(self, event):
        self.timer.stop()
        if self.do_task:
            try:
                self.do_task.write([False] * 8)
                self.do_task.stop()
                self.do_task.close()
            except Exception:
                log.warning("关闭调试窗口时DO清理失败", exc_info=True)
        if self.ai_task:
            try:
                self.ai_task.stop()
                self.ai_task.close()
            except Exception:
                log.warning("关闭调试窗口时AI清理失败", exc_info=True)
        event.accept()


# ============================================================================
# [SECTION 5] 核心 UI 组件 (View Components)
# ============================================================================

class StationWidget(QFrame):
    sig_remove = pyqtSignal(object)

    def __init__(self, idx, log_signal):
        super().__init__()
        self.setObjectName("Card")
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.setMinimumHeight(480)

        self.idx = idx
        self.global_log = log_signal
        self.worker = None
        self.hardware_connected = False
        self.data_x = deque(maxlen=PLOT_MAX_POINTS)
        self.data_y = deque(maxlen=PLOT_MAX_POINTS)
        self.start_time = 0
        self._accepting_data = False
        self.init_ui()
        self.setup_breathing_animation()

    def setup_breathing_animation(self):
        self.glow_effect = QGraphicsDropShadowEffect(self)
        self.glow_effect.setBlurRadius(40)
        self.glow_effect.setYOffset(4)
        self.default_shadow_color = QColor(0, 0, 0, 25)
        self.glow_effect.setColor(self.default_shadow_color)
        self.setGraphicsEffect(self.glow_effect)
        self.glow_anim = QPropertyAnimation(self.glow_effect, b"color")
        self.glow_anim.setDuration(1500)
        self.glow_anim.setLoopCount(-1)
        self.glow_anim.setEasingCurve(QEasingCurve.Type.InOutSine)

    def set_glow_state(self, state):
        self.glow_anim.stop()
        if state == "run":
            self._start_anim(QColor("#30D158"), 3000)
        elif state == "error":
            self._start_anim(QColor("#FF453A"), 800)
        elif state == "pause":
            self._start_anim(QColor("#FF9F0A"), 2000)
        else:
            self.glow_effect.setBlurRadius(40)
            self.glow_effect.setColor(self.default_shadow_color)

    def _start_anim(self, color, duration):
        start_c = QColor(color)
        start_c.setAlpha(40)
        end_c = QColor(color)
        end_c.setAlpha(220)
        self.glow_effect.setBlurRadius(60 if duration < 1000 else 40)
        self.glow_anim.setStartValue(start_c)
        self.glow_anim.setKeyValueAt(0.5, end_c)
        self.glow_anim.setEndValue(start_c)
        self.glow_anim.setDuration(duration)
        self.glow_anim.start()

    def play_entrance_animation(self):
        opacity_effect = QGraphicsOpacityEffect(self)
        opacity_effect.setOpacity(0.0)
        self.setGraphicsEffect(opacity_effect)

        self._entrance_anim = QPropertyAnimation(opacity_effect, b"opacity")
        self._entrance_anim.setDuration(400)
        self._entrance_anim.setStartValue(0.0)
        self._entrance_anim.setEndValue(1.0)
        self._entrance_anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._entrance_anim.finished.connect(self._restore_glow_effect)
        self._entrance_anim.start()

    def _restore_glow_effect(self):
        self.setup_breathing_animation()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(24, 24, 24, 24)

        # Header
        h_lay = QHBoxLayout()
        self.lbl_title = QLabel(f"Station {self.idx}")
        self.lbl_title.setObjectName("CardTitle")

        self.lbl_status = QLabel("待机")
        self.lbl_status.setStyleSheet(STATUS_STYLES["stop"])

        self.btn_delete = QPushButton("✕")
        self.btn_delete.setObjectName("BtnDeleteCard")
        self.btn_delete.setFixedSize(30, 30)
        self.btn_delete.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_delete.clicked.connect(lambda: self.sig_remove.emit(self))

        h_lay.addWidget(self.lbl_title)
        h_lay.addStretch()
        h_lay.addWidget(self.lbl_status)
        h_lay.addSpacing(12)
        h_lay.addWidget(self.btn_delete)
        layout.addLayout(h_lay)

        # Config
        c_lay = QHBoxLayout()
        c_lay.setSpacing(8)
        self.in_dev = QLineEdit("Dev1")
        self.in_dev.setPlaceholderText("Device")
        self.in_dev.setFixedWidth(70)
        self.combo_group = QComboBox()
        self.combo_group.addItems([f"Group {i} ({i*8}-{i*8+7})" for i in range(4)])
        self.combo_group.setCurrentIndex((self.idx - 1) % 4)
        self.btn_connect = QPushButton("连接")
        self.btn_connect.setObjectName("BtnSecondary")
        self.btn_connect.setCheckable(True)
        self.btn_connect.setFixedWidth(70)
        self.btn_connect.clicked.connect(self.toggle_connection)
        lbl_dev = QLabel("设备:")
        lbl_dev.setFixedWidth(36)
        c_lay.addWidget(lbl_dev)
        c_lay.addWidget(self.in_dev)
        c_lay.addWidget(self.combo_group)
        c_lay.addWidget(self.btn_connect)
        layout.addLayout(c_lay)

        # Params
        p_lay = QGridLayout()
        p_lay.setSpacing(10)
        p_lay.setContentsMargins(0, 4, 0, 4)
        self.in_cycles = QLineEdit("350")
        self.in_cycles.setValidator(QIntValidator(1, 999999))
        self.in_target = QLineEdit("2.02")
        self.in_target.setValidator(QDoubleValidator(0.01, 10.0, 2))
        self.in_floor = QLineEdit("0.02")
        self.in_floor.setValidator(QDoubleValidator(0.0, 10.0, 2))
        self.in_max = QLineEdit("2.5")
        self.in_max.setValidator(QDoubleValidator(0.1, 20.0, 2))
        self.in_max.setStyleSheet("color: #FF453A; font-weight: bold;")
        p_lay.addWidget(QLabel("目标循环:"), 0, 0)
        p_lay.addWidget(self.in_cycles, 0, 1)
        p_lay.addWidget(QLabel("高压 (Bar):"), 0, 2)
        p_lay.addWidget(self.in_target, 0, 3)
        p_lay.addWidget(QLabel("低压 (Bar):"), 1, 0)
        p_lay.addWidget(self.in_floor, 1, 1)
        p_lay.addWidget(QLabel("保护上限:"), 1, 2)
        p_lay.addWidget(self.in_max, 1, 3)
        layout.addLayout(p_lay)

        # Chart
        self.plot = pg.PlotWidget()
        self.plot.setBackground('#FFFFFF')
        self.plot.setMinimumHeight(160)
        self.plot.getAxis('left').setPen('#8E8E93')
        self.plot.getAxis('bottom').setPen('#8E8E93')
        self.plot.showGrid(x=True, y=True, alpha=0.1)
        self.plot.setDownsampling(auto=True, mode='peak')
        self.plot.setClipToView(True)
        self.curve = self.plot.plot(pen=pg.mkPen('#007AFF', width=2))
        layout.addWidget(self.plot)

        # Info Panel
        i_lay = QHBoxLayout()

        v_time = QVBoxLayout()
        self.lbl_timer = QLabel("--")
        self.lbl_timer.setStyleSheet("font-size: 22px; font-weight: bold; color: #FF9F0A;")
        lbl_t = QLabel("倒计时 (s)")
        lbl_t.setProperty("class", "SubLabel")
        v_time.addWidget(lbl_t)
        v_time.addWidget(self.lbl_timer)

        v_prog = QVBoxLayout()
        v_prog.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_progress_val = QLabel("0 / 350")
        self.lbl_progress_val.setStyleSheet("font-size: 22px; font-weight: bold; color: #1C1C1E;")
        lbl_prog = QLabel("循环进度")
        lbl_prog.setProperty("class", "SubLabel")
        v_prog.addWidget(lbl_prog)
        v_prog.addWidget(self.lbl_progress_val)

        v_pres = QVBoxLayout()
        v_pres.setAlignment(Qt.AlignmentFlag.AlignRight)
        self.lbl_pressure = QLabel("0.00")
        self.lbl_pressure.setStyleSheet("font-size: 28px; font-weight: 700; color: #007AFF;")
        self.lbl_pressure.setAlignment(Qt.AlignmentFlag.AlignRight)
        lbl_p_t = QLabel("压力 (Bar)")
        lbl_p_t.setProperty("class", "SubLabel")
        lbl_p_t.setAlignment(Qt.AlignmentFlag.AlignRight)
        v_pres.addWidget(lbl_p_t)
        v_pres.addWidget(self.lbl_pressure)

        i_lay.addLayout(v_time)
        i_lay.addStretch()
        i_lay.addLayout(v_prog)
        i_lay.addStretch()
        i_lay.addLayout(v_pres)
        layout.addLayout(i_lay)
        layout.addStretch()

        # Buttons
        b_lay = QHBoxLayout()
        b_lay.setSpacing(10)
        self.btn_manual = QPushButton("调试")
        self.btn_manual.setObjectName("BtnSecondary")
        self.btn_manual.clicked.connect(self.open_manual)

        self.btn_start = QPushButton("开始测试")
        self.btn_start.setObjectName("BtnPrimary")
        self.btn_start.setEnabled(False)
        self.btn_start.clicked.connect(self.start_test)

        self.btn_stop = QPushButton("紧急停止")
        self.btn_stop.setObjectName("BtnDanger")
        self.btn_stop.setEnabled(False)
        self.btn_stop.clicked.connect(self.stop_test)

        b_lay.addWidget(self.btn_manual)
        b_lay.addWidget(self.btn_start, stretch=2)
        b_lay.addWidget(self.btn_stop)
        layout.addLayout(b_lay)

    def toggle_connection(self):
        if self.btn_connect.isChecked():
            dev_name = self.in_dev.text().strip()
            if not dev_name:
                QMessageBox.warning(self, "输入错误", "请输入有效的设备名称")
                self.btn_connect.setChecked(False)
                return
            offset = self.combo_group.currentIndex() * 8
            if not SIMULATION_MODE:
                try:
                    with nidaqmx.Task() as t:
                        t.do_channels.add_do_chan(
                            f"{dev_name}/port0/line{offset}:{offset+7}",
                            line_grouping=LineGrouping.CHAN_PER_LINE)
                except Exception as e:
                    QMessageBox.warning(self, "连接失败", f"无法连接到硬件:\n{e}")
                    self.btn_connect.setChecked(False)
                    return

            self.hardware_connected = True
            self.in_dev.setEnabled(False)
            self.combo_group.setEnabled(False)
            self.btn_connect.setText("已连接")
            self.btn_connect.setObjectName("BtnSuccess")
            self.btn_connect.setStyleSheet("")
            self.btn_start.setEnabled(True)
            self.global_log.emit(f"[Station {self.idx}] 硬件已连接")
        else:
            self.hardware_connected = False
            self.in_dev.setEnabled(True)
            self.combo_group.setEnabled(True)
            self.btn_connect.setText("连接")
            self.btn_connect.setObjectName("BtnSecondary")
            self.btn_connect.setStyleSheet("")
            self.btn_start.setEnabled(False)
            self.global_log.emit(f"[Station {self.idx}] 硬件断开")

    def start_test(self):
        if not self.hardware_connected and not SIMULATION_MODE:
            QMessageBox.warning(self, "未连接", "请先点击'连接'按钮锁定硬件配置。")
            return

        if self.worker and self.worker.isRunning():
            self.toggle_pause()
            return

        try:
            cycles = validate_positive_int(self.in_cycles.text(), "目标循环")
            target_p = validate_positive_float(self.in_target.text(), "高压目标", 0.01, 20.0)
            floor_p = validate_positive_float(self.in_floor.text(), "低压目标", 0.0, 20.0)
            max_p = validate_positive_float(self.in_max.text(), "保护上限", 0.1, 30.0)
        except ValueError as e:
            QMessageBox.warning(self, "参数错误", str(e))
            return

        if floor_p >= target_p:
            QMessageBox.warning(self, "参数错误", "低压阈值必须小于高压目标")
            return
        if max_p <= target_p:
            QMessageBox.warning(self, "参数错误", "保护上限必须大于高压目标")
            return

        dev_name = self.in_dev.text().strip()
        offset = self.combo_group.currentIndex() * 8
        cfg = {
            'device': dev_name, 'cycles': str(cycles),
            'target_p': str(target_p), 'floor_p': str(floor_p),
            'max_p': str(max_p), 'simulation': SIMULATION_MODE,
        }

        self.data_x.clear()
        self.data_y.clear()
        self.curve.setData([], [])
        self.start_time = time.time()
        self.lbl_progress_val.setText(f"0 / {cycles}")

        self.worker = TestWorker(cfg, offset, os.getcwd())
        self.worker.sig_pressure.connect(self.update_gui_data)
        self.worker.sig_timer.connect(self.lbl_timer.setText)
        self.worker.sig_status.connect(self.update_status)
        self.worker.sig_progress.connect(self.update_progress)
        self.worker.sig_log.connect(
            lambda m: self.global_log.emit(f"[Station {self.idx}] {m}"))
        self.worker.sig_finished.connect(self.on_finish)
        self.worker.sig_error.connect(self.on_error)
        self.worker.sig_button_update.connect(self.update_start_btn_text)
        self.worker.sig_result.connect(self._on_result)
        self._last_run_success = None

        self.btn_start.setText("暂停测试")
        self.btn_start.setStyleSheet(
            "background-color: #FF9F0A; color: white; border: none;")
        self.btn_manual.setEnabled(False)
        self.btn_connect.setEnabled(False)
        self.btn_stop.setEnabled(True)
        self.btn_delete.setVisible(False)

        self._accepting_data = True
        self.set_glow_state("run")
        self.worker.start()

    def toggle_pause(self):
        if not self.worker:
            return

        if self.worker.is_paused:
            self.worker.set_pause(False)
            self.btn_start.setText("暂停测试")
            self.btn_start.setStyleSheet(
                "background-color: #FF9F0A; color: white; border: none;")
            self.set_glow_state("run")
        else:
            self.worker.set_pause(True)
            self.btn_start.setText("继续测试")
            self.btn_start.setStyleSheet(
                "background-color: #30D158; color: white; border: none;")
            self.set_glow_state("pause")

    def update_start_btn_text(self, mode):
        if mode == "continue":
            self.btn_start.setText("继续测试")
            self.btn_start.setStyleSheet(
                "background-color: #30D158; color: white; border: none;")
            self.set_glow_state("error")

    def open_manual(self):
        ManualControlDialog(
            self.in_dev.text(), self.combo_group.currentIndex() * 8,
            self, self).exec()

    def stop_test(self):
        self._accepting_data = False
        if self.worker:
            self.worker.stop()

    def update_gui_data(self, val):
        if not self._accepting_data:
            return
        self.lbl_pressure.setText(f"{val:.2f}")
        self.data_x.append(time.time() - self.start_time)
        self.data_y.append(val)
        self.curve.setData(list(self.data_x), list(self.data_y))

    def update_status(self, msg, style):
        self.lbl_status.setText(msg)
        self.lbl_status.setStyleSheet(style)

    def update_progress(self, current):
        self.lbl_progress_val.setText(f"{current} / {self.in_cycles.text()}")

    def on_error(self, err_msg):
        self.set_glow_state("error")
        self.global_log.emit(f"[Station {self.idx} 故障] {err_msg}")

    def _on_result(self, success):
        self._last_run_success = success

    def on_finish(self):
        self._accepting_data = False
        self.btn_start.setText("开始测试")
        self.btn_start.setObjectName("BtnPrimary")
        self.btn_start.setStyleSheet("")
        self.btn_start.setEnabled(True)
        self.btn_manual.setEnabled(True)
        self.btn_connect.setEnabled(True)
        self.btn_stop.setEnabled(False)
        self.btn_delete.setVisible(True)
        self.lbl_timer.setText("--")
        if self._last_run_success:
            self.set_glow_state("idle")
        else:
            self.set_glow_state("error")


# ============================================================================
# [SECTION 6] 主窗口 (Main Application Window)
# ============================================================================

class AnimatedPanel(QFrame):
    """可动画展开/折叠的面板，同时驱动 minimumHeight 和 maximumHeight"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self._expanded = True
        self._target_height = 60

        self._anim_min = QPropertyAnimation(self, b"minimumHeight")
        self._anim_min.setDuration(250)
        self._anim_min.setEasingCurve(QEasingCurve.Type.OutCubic)

        self._anim_max = QPropertyAnimation(self, b"maximumHeight")
        self._anim_max.setDuration(250)
        self._anim_max.setEasingCurve(QEasingCurve.Type.OutCubic)

        self._anim_group = QParallelAnimationGroup(self)
        self._anim_group.addAnimation(self._anim_min)
        self._anim_group.addAnimation(self._anim_max)

    def toggle(self):
        self._expanded = not self._expanded
        self._anim_group.stop()
        if self._expanded:
            self._anim_min.setStartValue(0)
            self._anim_min.setEndValue(self._target_height)
            self._anim_max.setStartValue(0)
            self._anim_max.setEndValue(self._target_height)
        else:
            self._anim_min.setStartValue(self.height())
            self._anim_min.setEndValue(0)
            self._anim_max.setStartValue(self.height())
            self._anim_max.setEndValue(0)
        self._anim_group.start()

    @property
    def expanded(self):
        return self._expanded


class MainWindow(QMainWindow):
    sig_log = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Compressor Lifetime Rev3.2")
        self.resize(1440, 960)
        self.stations = []

        main_w = QWidget()
        main_w.setObjectName("CentralWidget")
        self.setCentralWidget(main_w)
        layout = QVBoxLayout(main_w)
        layout.setSpacing(0)
        layout.setContentsMargins(0, 0, 0, 0)

        # Top Bar
        top_bar = QFrame()
        top_bar.setStyleSheet("background-color: #F9F9F9; border-bottom: 1px solid #E5E5EA;")
        top_bar.setFixedHeight(40)
        tb_layout = QHBoxLayout(top_bar)
        tb_layout.setContentsMargins(10, 0, 10, 0)
        self.btn_toggle = QPushButton("⚙  系统设置 ▼")
        self.btn_toggle.setObjectName("BtnToggleSettings")
        self.btn_toggle.clicked.connect(self.toggle_settings)
        tb_layout.addWidget(self.btn_toggle)
        tb_layout.addStretch()
        layout.addWidget(top_bar)

        # Settings Panel (animated)
        self.settings_panel = AnimatedPanel()
        self.settings_panel.setObjectName("SettingsPanel")
        self.settings_panel.setMinimumHeight(60)
        self.settings_panel.setMaximumHeight(60)
        self.settings_panel._target_height = 60
        sp_layout = QHBoxLayout(self.settings_panel)
        sp_layout.setContentsMargins(20, 0, 20, 0)
        sp_layout.setSpacing(12)

        self.btn_add = QPushButton(" + 增加台架 ")
        self.btn_add.setObjectName("BtnAdd")
        self.btn_add.setFixedSize(110, 36)
        self.btn_add.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_add.clicked.connect(self.add_station)

        self.chk_sim = QCheckBox("仿真模式 (Simulation)")
        self.chk_sim.setStyleSheet("font-weight: bold; color: #007AFF;")
        self.chk_sim.stateChanged.connect(self.toggle_sim)

        self.lbl_dir = QLabel(os.getcwd())
        self.lbl_dir.setStyleSheet("color: #8E8E93;")
        self.lbl_dir.setMinimumWidth(100)

        btn_dir = QPushButton("更改路径")
        btn_dir.setObjectName("BtnSecondary")
        btn_dir.setFixedSize(100, 36)
        btn_dir.clicked.connect(self.set_dir)

        sp_layout.addWidget(self.btn_add)
        line = QFrame()
        line.setFrameShape(QFrame.Shape.VLine)
        line.setStyleSheet("color: #E5E5EA;")
        sp_layout.addWidget(line)
        sp_layout.addWidget(self.chk_sim)
        sp_layout.addStretch()
        sp_layout.addWidget(self.lbl_dir)
        sp_layout.addWidget(btn_dir)
        layout.addWidget(self.settings_panel)

        # Content Splitter
        self.splitter = QSplitter(Qt.Orientation.Vertical)
        self.splitter.setHandleWidth(6)
        self.splitter.setChildrenCollapsible(False)

        # Scroll Area
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        grid_w = QWidget()
        grid_w.setObjectName("ScrollContents")
        self.grid = QGridLayout(grid_w)
        self.grid.setSpacing(20)
        self.grid.setContentsMargins(20, 20, 20, 20)
        scroll.setWidget(grid_w)
        self.splitter.addWidget(scroll)

        # Log Area
        log_cont = QFrame()
        log_cont.setObjectName("LogContainer")
        log_lay = QVBoxLayout(log_cont)
        log_lay.setContentsMargins(10, 10, 10, 10)
        lbl_log = QLabel("System Log")
        lbl_log.setStyleSheet(
            "color: #8E8E93; font-weight: bold; font-size: 11px; "
            "letter-spacing: 0.3px;")
        log_lay.addWidget(lbl_log)
        self.log_widget = QTextEdit()
        self.log_widget.setReadOnly(True)
        log_lay.addWidget(self.log_widget)
        self.splitter.addWidget(log_cont)
        self.splitter.setSizes([800, 200])

        layout.addWidget(self.splitter)
        self.sig_log.connect(self.append_log)

        set_keep_awake(True)
        self.add_station()

    def add_station(self):
        existing_ids = {s.idx for s in self.stations}
        new_idx = 1
        while new_idx in existing_ids:
            new_idx += 1

        st = StationWidget(new_idx, self.sig_log)
        st.sig_remove.connect(self.delete_specific_station)
        self.stations.append(st)
        self.rearrange_layout()
        st.play_entrance_animation()
        self.append_log(f"系统: 已增加台架 (ID: {new_idx})")

    def delete_specific_station(self, station_widget):
        if len(self.stations) <= 1:
            QMessageBox.warning(self, "操作无效", "系统至少需要保留一个台架。")
            return

        if station_widget.worker and station_widget.worker.isRunning():
            QMessageBox.critical(
                self, "禁止删除",
                f"台架 {station_widget.idx} 正在运行中，请先停止测试后再删除。")
            return

        idx = station_widget.idx
        self.stations.remove(station_widget)
        self.grid.removeWidget(station_widget)
        station_widget.deleteLater()

        self.rearrange_layout()
        self.append_log(f"系统: 已移除台架 (ID: {idx})")

    def rearrange_layout(self):
        for i in reversed(range(self.grid.count())):
            item = self.grid.itemAt(i)
            if item and item.widget():
                item.widget().setParent(None)

        count = len(self.stations)
        cols = 1 if count == 1 else (2 if count <= 4 else 3)

        max_grid_dim = max(count // cols + 2, cols + 1, 10)
        for i in range(max_grid_dim):
            self.grid.setColumnStretch(i, 0)
            self.grid.setRowStretch(i, 0)
        for c in range(cols):
            self.grid.setColumnStretch(c, 1)
        rows = (count + cols - 1) // cols
        for r in range(rows):
            self.grid.setRowStretch(r, 1)

        for i, st in enumerate(self.stations):
            self.grid.addWidget(st, i // cols, i % cols)
            st.setVisible(True)

    def toggle_settings(self):
        self.settings_panel.toggle()
        is_exp = self.settings_panel.expanded
        self.btn_toggle.setText("⚙  系统设置 " + ("▼" if is_exp else "▶"))

    def toggle_sim(self, s):
        global SIMULATION_MODE
        SIMULATION_MODE = (s == 2)
        self.append_log(f"系统模式切换: {'仿真' if SIMULATION_MODE else '硬件'}")

    def set_dir(self):
        d = QFileDialog.getExistingDirectory(self, "选择日志保存路径")
        if d:
            self.lbl_dir.setText(d)
            try:
                os.chdir(d)
            except OSError as e:
                QMessageBox.warning(self, "路径错误", f"无法切换到目标路径:\n{e}")

    def append_log(self, t):
        self.log_widget.append(f"[{datetime.now().strftime('%H:%M:%S')}] {t}")
        sb = self.log_widget.verticalScrollBar()
        sb.setValue(sb.maximum())

    def closeEvent(self, event):
        set_keep_awake(False)
        for s in self.stations:
            if s.worker and s.worker.isRunning():
                s.worker.stop()
                s.worker.wait(3000)
        event.accept()


# ============================================================================
# [SECTION 7] 程序入口 (Entry Point)
# ============================================================================

if __name__ == '__main__':
    logging.basicConfig(level=logging.WARNING,
                        format="%(asctime)s [%(levelname)s] %(message)s")

    os.environ["QT_SCALE_FACTOR"] = "1"
    if hasattr(Qt.ApplicationAttribute, 'AA_EnableHighDpiScaling'):
        QApplication.setAttribute(Qt.ApplicationAttribute.AA_EnableHighDpiScaling, True)

    app = QApplication(sys.argv)

    app.setStyleSheet(IOS_LIGHT_THEME)
    app.setFont(QFont("Segoe UI", 9))

    w = MainWindow()
    w.showMaximized()
    sys.exit(app.exec())
