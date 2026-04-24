# -*- coding: utf-8 -*-
"""
==============================================================================
项目名称 (Project)   : Compressor Lifetime Test System (压缩机寿命耐久测试系统)
文件名称 (Filename)  : compressor_lifetime_3.1.py
版本号   (Version)   : Rev 3.1
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

需要修改的点：1
1.V3硬件控制逻辑的修改
2. Labview接线的修改，需要修改引脚定义

==============================================================================
"""

# --- 1. 标准库导入 ---
import sys
import os
import time
import random
import csv
import ctypes
from datetime import datetime
from collections import deque
import statistics # 用于中值滤波

# --- 2. 第三方库导入 (GUI & Plotting) ---
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QGridLayout, QLabel, 
                             QLineEdit, QPushButton, QCheckBox, QTextEdit, 
                             QFileDialog, QSplitter, QMessageBox,
                             QScrollArea, QDialog, QComboBox,
                             QSizePolicy, QFrame, QGraphicsDropShadowEffect)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QPropertyAnimation, QEasingCurve, QTimer, QRect, QSettings
from PyQt6.QtGui import QFont, QColor, QPalette

import pyqtgraph as pg
pg.setConfigOptions(antialias=True)

# --- 3. 硬件驱动导入 (NI-DAQmx) ---
import nidaqmx
from nidaqmx.constants import LineGrouping, TerminalConfiguration, AcquisitionType


# ============================================================================
# [SECTION 1] 全局配置与样式 (Global Configuration)
# ============================================================================

IDX_MAP = {
    0: "V1 阀门", 1: "V2 阀门", 2: "V3 阀门", 3: "压缩机",
    4: "压力计供电", 5: "计数供电", 6: "计数信号", 7: "蜂鸣器/报警"
}

SIMULATION_MODE = False  

PHASE_1_REPEAT = 4
PHASE_2_REPEAT = 14
ENABLE_ENTRY_ANIMATION = False

STATUS_STYLES = {
    "run": "color: #34C759; font-weight: bold; font-size: 15px; background-color: transparent;",
    "stop": "color: #8E8E93; font-weight: bold; font-size: 15px; background-color: transparent;",
    "err": "color: #FF3B30; font-weight: bold; font-size: 15px; background-color: transparent;",
    "pause": "color: #FF9500; font-weight: bold; font-size: 15px; background-color: transparent;",
}

IOS_LIGHT_THEME = """
    QWidget {
        background-color: #F9F9F9; color: #1C1C1E;
        font-family: "Segoe UI", "Microsoft YaHei", sans-serif; font-size: 14px;
    }
    QMainWindow, QWidget#CentralWidget { background-color: #F2F2F7; }
    
    /* 面板与卡片 */
    QFrame#SettingsPanel { background-color: #FFFFFF; border-bottom: 1px solid #E5E5EA; }
    QFrame#Card { background-color: #FFFFFF; border-radius: 16px; border: 1px solid #E5E5EA; }
    
    /* 标签 */
    QLabel#CardTitle { font-size: 18px; font-weight: bold; color: #000000; background-color: transparent; }
    QLabel { background-color: transparent; color: #1C1C1E; }
    QLabel.SubLabel { font-size: 12px; color: #8E8E93; }

    /* 输入框 */
    QLineEdit, QComboBox {
        background-color: #F2F2F7; border: 1px solid #E5E5EA; border-radius: 8px;
        padding: 6px 10px; color: #000000;
    }
    QLineEdit:focus { border: 1px solid #007AFF; background-color: #FFFFFF; }
    QComboBox::drop-down { border: none; }

    /* 按钮组 */
    QPushButton { border-radius: 10px; padding: 8px 16px; font-weight: 600; font-size: 14px; }
    QPushButton#BtnPrimary { background-color: #007AFF; color: white; border: none; }
    QPushButton#BtnPrimary:hover { background-color: #0062CC; }
    QPushButton#BtnPrimary:disabled { background-color: #B4D9FF; }
    
    QPushButton#BtnSuccess { background-color: #34C759; color: white; border: none; }
    QPushButton#BtnSuccess:hover { background-color: #2DA84E; }
    
    QPushButton#BtnSecondary { background-color: #FFFFFF; color: #007AFF; border: 1px solid #D1D1D6; }
    QPushButton#BtnSecondary:hover { background-color: #F2F2F7; }
    
    QPushButton#BtnDanger { background-color: #FF3B30; color: white; border: none; }
    QPushButton#BtnDanger:hover { background-color: #D63027; }
    QPushButton#BtnDanger:disabled { background-color: #FFB2AC; }

    QPushButton#BtnAdd { background-color: #E8F5E9; color: #2E7D32; border: 1px solid #C8E6C9; }
    
    /* 删除按钮特殊样式 */
    QPushButton#BtnDeleteCard { 
        background-color: transparent; color: #C62828; border: none; 
        font-weight: bold; font-size: 18px; padding: 0px;
    }
    QPushButton#BtnDeleteCard:hover { color: #FF0000; background-color: #FFEBEE; border-radius: 15px;}
    
    QPushButton#BtnToggleSettings {
        background-color: transparent; color: #8E8E93; border: none;
        font-weight: bold; text-align: left; padding-left: 20px;
    }
    QPushButton#BtnToggleSettings:hover { color: #007AFF; }

    /* 其他组件 */
    QScrollArea { border: none; background-color: transparent; }
    QWidget#ScrollContents { background-color: transparent; }
    QSplitter::handle { background-color: #E5E5EA; margin: 1px; }
    QSplitter::handle:hover { background-color: #007AFF; }
    QTextEdit {
        background-color: #F9F9F9; color: #333333; border-radius: 8px;
        font-family: "Menlo", "Consolas", monospace; border: 1px solid #E5E5EA;
    }
    QDialog { background-color: #FFFFFF; }
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
            ctypes.windll.kernel32.SetThreadExecutionState(ES_CONTINUOUS | ES_SYSTEM_REQUIRED | ES_DISPLAY_REQUIRED)
        else:
            ctypes.windll.kernel32.SetThreadExecutionState(ES_CONTINUOUS)
    except: pass


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
        try:
            self.dev_name = str(config['device']).strip()
            self.target_cycles = int(config['cycles'])
            self.target_p = float(config['target_p'])
            self.floor_p = float(config['floor_p'])
            self.max_p = float(config['max_p'])
            self.sim_mode = bool(config['simulation'])
            self.station_idx = int(config.get('station_idx', 0))
        except (KeyError, TypeError, ValueError) as e:
            raise ValueError(f"配置参数无效: {e}")

        if not self.dev_name:
            raise ValueError("设备名称不能为空")
        if self.target_cycles <= 0:
            raise ValueError("目标循环次数必须大于 0")
        if self.floor_p < 0:
            raise ValueError("低压阈值不能小于 0")
        if self.target_p <= self.floor_p:
            raise ValueError("高压阈值必须大于低压阈值")
        if self.max_p <= self.target_p:
            raise ValueError("保护上限必须大于高压阈值")

        self._sim_p_val = 0.0
        self._last_pressure = 0.0 
        self._first_read = True 
        self.pressure_deque = deque(maxlen=4)
        self.step_max_p = 0.0
        self.step_min_p = 99.9  
        self.fault_triggered = False
        self.last_do_states = [False] * 8
        self._in_pause_handler = False

    def run(self):
        try:
            self.setup_hardware()
            self.create_log_file()
            self.sig_log.emit(f"启动: {self.dev_name} [Line {self.offset}-{self.offset+7}]")

            current_cycle = 1
            while current_cycle <= self.target_cycles:
                if not self.is_running: break

                try:
                    self.check_pause_state() 
                    self.sig_status.emit(f"循环 {current_cycle}: 启动", STATUS_STYLES["run"])
                    
                    if not self.run_phase_1(current_cycle): 
                        if not self.is_running: break
                        raise RuntimeError("阶段一异常退出，且未收到停止指令")

                    if not self.run_phase_2(current_cycle):
                        if not self.is_running: break
                        raise RuntimeError("阶段二异常退出，且未收到停止指令")

                    self.sig_status.emit(f"循环 {current_cycle}: 计数器触发", STATUS_STYLES["run"])
                    self._trigger_counter()
                    
                    if not self.sleep_smart(1.0): break
                    
                    self.sig_progress.emit(current_cycle)
                    current_cycle += 1
                
                except RetryCycleError:
                    if not self.is_running: break
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
            else:
                self.sig_status.emit("已停止", STATUS_STYLES["err"])

        except Exception as e:
            self.sig_error.emit(f"系统异常: {str(e)}")
            self.emergency_shutdown() 
        finally:
            self.cleanup()
            self.sig_finished.emit()

    def check_pause_state(self):
        if self._in_pause_handler:
            return
        if self.is_paused and self.is_running:
            self._in_pause_handler = True
            try:
                self.sig_status.emit("已暂停 / 等待恢复", STATUS_STYLES["pause"])
                temp_safe_states = list(self.last_do_states)
                temp_safe_states[3] = False 
                if self.fault_triggered:
                    temp_safe_states[7] = True 
                    self.sig_log.emit(f"故障暂停: 等待用户操作 (复位模式)")
                else:
                    self.sig_log.emit(f"手动暂停: 保持状态 (继续模式)")
                
                if not self.sim_mode and self.do_task:
                    try:
                        self.do_task.write(temp_safe_states)
                    except Exception as e:
                        self.sig_log.emit(f"暂停态输出失败: {e}")
                
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
            finally:
                self._in_pause_handler = False

    def trigger_fault(self, error_msg):
        if self.fault_triggered and self.is_paused:
            return
        self.fault_triggered = True
        self.is_paused = True
        self.sig_error.emit(error_msg)
        self.sig_button_update.emit("continue")
        if self._in_pause_handler:
            return
        self.check_pause_state()

    def set_pause(self, paused):
        self.is_paused = paused

    def stop(self):
        self.is_running = False
        self.is_paused = False 
        self.sig_log.emit("!!! 用户触发紧急停止 !!!")
        self.sig_status.emit("正在停止...", STATUS_STYLES["err"])
        self.emergency_shutdown()

    def setup_hardware(self):
        if self.sim_mode: return
        lines = f"{self.dev_name}/port0/line{self.offset}:{self.offset+7}"
        self.do_task = nidaqmx.Task()
        try:
            self.do_task.do_channels.add_do_chan(lines, line_grouping=LineGrouping.CHAN_PER_LINE)
            self.do_task.start()
            self.do_task.write([False]*8)
        except Exception as e:
            self.do_task.close()
            raise RuntimeError(f"DO初始化失败: {e}")
        
        ai_idx = self.offset // 8
        ai_chan = f"{self.dev_name}/ai{ai_idx}"
        self.ai_task = nidaqmx.Task()
        try:
            self.ai_task.ai_channels.add_ai_voltage_chan(
                ai_chan, terminal_config=TerminalConfiguration.RSE, min_val=-10.0, max_val=10.0
            )
            self.ai_task.timing.cfg_samp_clk_timing(
                rate=500, sample_mode=AcquisitionType.CONTINUOUS, samps_per_chan=1000
            )
            self.ai_task.start()
        except Exception as e:
            self.ai_task.close()
            self.do_task.close()
            raise RuntimeError(f"AI初始化失败: {e}")

    def read_pressure(self, silent=False):
        if self.sim_mode: 
            return self._simulate_pressure(silent)
    
        try:
        # 1. 硬件层：读取所有可用数据（一次可能拿到 10-50 个点）
            data = self.ai_task.read(number_of_samples_per_channel=nidaqmx.constants.READ_ALL_AVAILABLE)
        
            if len(data) == 0:
                return self._last_pressure

        # 2. 【核心修改】抗脉冲干扰处理
        # 针对你的图表：因为只有尖峰，只要取“中位数”，尖峰就会被 100% 完美丢弃
            if len(data) >= 3:
            # 使用中位数，它比平均值更能抗尖峰
                current_volts = statistics.median(data)
            else:
                current_volts = data[0]

        # 3. 物理量转换
            current_p = max(0, (current_volts - 1.0) * 2.5)

        # 4. 软件层：滑动平均 (平滑趋势)
        # 将干净的数据放入队列
            self.pressure_deque.append(current_p)
        
        # 计算最终值
            filtered_p = sum(self.pressure_deque) / len(self.pressure_deque)
        # 死区截断 (Zero Cutoff) 零点漂移
            if filtered_p < 0.015:
                filtered_p = 0.0

            self._last_pressure = filtered_p
            
            if not silent: 
                self.sig_pressure.emit(filtered_p)
                
            self._update_stats(filtered_p)
            self._check_safety(filtered_p)
            return filtered_p

        except Exception as e:
            if self.is_running: raise e
            return 0.0

    def write_do(self, states):
        if not self.is_running: return
        if len(states) != 8:
            self.is_running = False
            self.sig_error.emit(f"写入硬件失败: DO 状态长度应为 8，实际为 {len(states)}")
            return
        self.last_do_states = list(states) 
        
        if self.sim_mode: return self._simulate_response(states)
        if self.do_task:
            try: self.do_task.write(states)
            except Exception as e:
                self.is_running = False
                self.sig_error.emit(f"写入硬件失败: {e}")

    def emergency_shutdown(self):
        if self.sim_mode: return
        if self.do_task: 
            try:
                self.do_task.stop(); self.do_task.start(); self.do_task.write([False]*8)
            except Exception as e:
                self.sig_log.emit(f"紧急停机输出失败: {e}")

    def run_phase_1(self, cycle):
        success_count = 0 
        for i in range(PHASE_1_REPEAT):
            self.check_pause_state() 
            self.step_max_p = 0.0; self.step_min_p = 99.9
            if not self.is_running: return False
            self.sig_status.emit(f"P1 ({i+1}/{PHASE_1_REPEAT}): 初始加压", STATUS_STYLES["run"])
            current_loop_reached = False; in_release_mode = False
            phase_duration = 90.0
            t_start = time.monotonic()
            paused_total = 0.0
            while True:
                if not self.is_running: return False
                
                if self.is_paused:
                    pause_start = time.monotonic()
                    self.check_pause_state()
                    paused_total += time.monotonic() - pause_start
                    continue
                
                elapsed = time.monotonic() - t_start - paused_total
                remaining = phase_duration - elapsed
                if remaining <= 0:
                    break

                self.sig_timer.emit(f"{remaining:.1f}")
                p = self.read_pressure()
                states = [False]*8; states[0]=True; states[4]=True; states[5]=True 
                if not in_release_mode:
                    states[3] = True 
                    if p >= self.target_p:
                        current_loop_reached = True; in_release_mode = True
                        states[3]=True; states[1]=True; states[2]=True; states[0]=False
                        self.sig_status.emit(f"P1 ({i+1}/{PHASE_1_REPEAT}): 达标泄压", STATUS_STYLES["run"])
                else:
                    states[3]=True; states[1]=True; states[2]=True; states[0]=False
                    if p <= self.floor_p:
                        in_release_mode = False
                        self.sig_status.emit(f"P1 ({i+1}/{PHASE_1_REPEAT}): 重新打压", STATUS_STYLES["run"])
                self.write_do(states); time.sleep(0.1)
            if current_loop_reached: success_count += 1
            else: self.sig_log.emit(f"警告: P1 第 {i+1} 次循环未达到目标压力")
            if not self.run_release_57s(cycle, f"P1 ({i+1}/{PHASE_1_REPEAT})"): return False
            self.log_csv(cycle, "Phase_1", f"{i+1}/{PHASE_1_REPEAT} Done", self.read_pressure(silent=True))
        if success_count == 0:
            self.trigger_fault(f"故障: 阶段一循环均未达到目标压力 {self.target_p} Bar")
            return False 
        return True

    def run_phase_2(self, cycle):
        for i in range(PHASE_2_REPEAT):
            self.check_pause_state() 
            self.step_max_p = 0.0; self.step_min_p = 99.9
            if not self.is_running: return False
            for j in range(10):
                if not self.is_running: return False
                if self.is_paused: self.check_pause_state() 
                
                self.sig_status.emit(f"P2 ({i+1}/{PHASE_2_REPEAT}): 脉冲 {j+1}/10", STATUS_STYLES["run"])
                if j == 9: self._run_complex_pulse()
                else: self._run_simple_pulse()
            if not self.run_release_57s(cycle, f"P2 ({i+1}/{PHASE_2_REPEAT})"): return False
            self.log_csv(cycle, "Phase_2", f"{i+1}/{PHASE_2_REPEAT} Done", self.read_pressure(silent=True))
        return True

    def run_release_57s(self, cycle, phase_name):
        self.sig_status.emit(f"{phase_name}: 泄压 (V2+V3)", STATUS_STYLES["run"])
        s_a = [False]*8; s_a[1]=True; s_a[2]=True; s_a[4]=True; s_a[5]=True
        self.write_do(s_a)
        if not self.sleep_smart(20.0): return False
        self.sig_status.emit(f"{phase_name}: 泄压 (V1)", STATUS_STYLES["run"])
        s_b = [False]*8; s_b[0]=True; s_b[4]=True; s_b[5]=True
        self.write_do(s_b)
        if not self.sleep_smart(37.0): return False
        return True

    def sleep_smart(self, duration):
        start = time.monotonic()
        paused_total = 0.0
        while True:
            if not self.is_running: return False
            if self.is_paused:
                pause_start = time.monotonic()
                self.check_pause_state()
                paused_total += time.monotonic() - pause_start
                continue

            elapsed = time.monotonic() - start - paused_total
            remaining = duration - elapsed
            if remaining <= 0:
                break

            self.sig_timer.emit(f"{remaining:.1f}")
            self.read_pressure() 
            time.sleep(0.1)
        self.sig_timer.emit("0.0")
        return True

    def _sleep_checked(self, duration):
        start = time.monotonic()
        paused_total = 0.0
        while True:
            if not self.is_running:
                return False
            if self.is_paused:
                pause_start = time.monotonic()
                self.check_pause_state()
                paused_total += time.monotonic() - pause_start
                continue

            elapsed = time.monotonic() - start - paused_total
            if elapsed >= duration:
                break

            self.read_pressure(silent=True)
            time.sleep(0.02)
        return True

    def finalize_success(self):
        if self.sim_mode: return
        try:
            if self.do_task: f = [False]*8; f[4]=True; f[5]=True; self.do_task.write(f)
        except Exception as e:
            self.sig_log.emit(f"结束态输出失败: {e}")

    def cleanup(self):
        if not self.sim_mode and self.do_task:
            try:
                states = [False]*8
                if self.fault_triggered: states[7] = True
                self.do_task.write(states); self.do_task.close()
            except Exception as e:
                self.sig_log.emit(f"DO 清理失败: {e}")
        if not self.sim_mode and self.ai_task:
            try:
                self.ai_task.close()
            except Exception as e:
                self.sig_log.emit(f"AI 清理失败: {e}")

    def create_log_file(self):
        ts = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        station_suffix = f"_St{self.station_idx}" if self.station_idx > 0 else ""
        self.csv_file = os.path.join(
            self.log_dir,
            f"Log_{self.dev_name}_Grp{self.offset//8}{station_suffix}_{ts}.csv"
        )
        with open(self.csv_file, 'w', newline='') as f:
            csv.writer(f).writerow(["Date", "Time", "Cycle", "Phase", "Step", "End_P", "Max_P", "Min_P"])

    def log_csv(self, cycle, phase, step, end_p):
        if not self.csv_file: return
        try:
            n = datetime.now()
            with open(self.csv_file, 'a', newline='') as f:
                csv.writer(f).writerow([n.strftime("%Y-%m-%d"), n.strftime("%H:%M:%S"), 
                                        cycle, phase, step, f"{end_p:.2f}", 
                                        f"{self.step_max_p:.2f}", f"{self.step_min_p:.2f}"])
        except Exception as e:
            self.sig_log.emit(f"日志写入失败: {e}")

    def _simulate_pressure(self, silent):
        time.sleep(0.02); noise = random.uniform(-0.05, 0.05)
        self._sim_p_val = max(0, self._sim_p_val + noise)
        if not silent: self.sig_pressure.emit(self._sim_p_val)
        self._update_stats(self._sim_p_val); self._check_safety(self._sim_p_val)
        return self._sim_p_val

    def _simulate_response(self, states):
        if states[3] and states[0]: self._sim_p_val += 0.15
        elif states[1] or states[2]: self._sim_p_val = max(0, self._sim_p_val - 0.3)
        elif states[0]: self._sim_p_val = max(0, self._sim_p_val - 0.05)

    def _update_stats(self, val):
        if val > self.step_max_p: self.step_max_p = val
        if val < self.step_min_p: self.step_min_p = val

    def _check_safety(self, val):
        if val > self.max_p and not self.fault_triggered:
            self.trigger_fault(f"压力超限: {val:.2f} > {self.max_p}")

    def _trigger_counter(self):
        s = [False]*8; s[1]=True; s[2]=True; s[4]=True; s[5]=True; s[6]=True
        self.write_do(s)

    def _run_simple_pulse(self):
        s_on = [False]*8; s_on[0]=True; s_on[3]=True; s_on[4]=True; s_on[5]=True
        self.write_do(s_on)
        if not self.sleep_smart(1.0): return
        s_off = [False]*8; s_off[0]=True; s_off[4]=True; s_off[5]=True
        self.write_do(s_off)
        if not self.sleep_smart(1.0): return

    def _run_complex_pulse(self):
        for _ in range(5):
            if not self.is_running: return
            s1 = [False]*8; s1[0]=True; s1[3]=True; s1[2]=True; s1[4]=True; s1[5]=True
            self.write_do(s1)
            if not self._sleep_checked(0.1): return
            s2 = [False]*8; s2[0]=True; s2[3]=True; s2[4]=True; s2[5]=True
            self.write_do(s2)
            if not self._sleep_checked(0.1): return
        for _ in range(5): 
            if not self.is_running: return
            s3 = [False]*8; s3[0]=True; s3[2]=True; s3[4]=True; s3[5]=True
            self.write_do(s3)
            if not self._sleep_checked(0.1): return
            s4 = [False]*8; s4[0]=True; s4[4]=True; s4[5]=True
            self.write_do(s4)
            if not self._sleep_checked(0.1): return


# ============================================================================
# [SECTION 4] 辅助 UI 组件 (Dialogs)
# ============================================================================

class ManualControlDialog(QDialog):
    def __init__(self, dev_name, offset, station_widget, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"调试模式 (Debug) - {dev_name}")
        self.setFixedSize(460, 640) # 稍微加高一点以容纳更多信息
        self.dev_name = dev_name; self.offset = offset
        self.station = station_widget
        self.do_task = None
        self.ai_task = None 
        self.current_states = [False] * 8; self.buttons = []
        self._sim_p = 0.0 
        
        # [新增] 调试用的滑动窗口，与 TestWorker 保持完全一致的逻辑
        self.debug_deque = deque(maxlen=4) 
        
        self.init_ui()
        self.start_tasks() 

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(15); layout.setContentsMargins(20, 20, 20, 20)

        title = QLabel(f"IO Control: Line {self.offset} - {self.offset+7}")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet("font-size: 18px; font-weight: bold; color: #333;")
        layout.addWidget(title)
        
        # --- [修改] 压力显示区域 ---
        p_frame = QFrame()
        p_frame.setStyleSheet("background-color: #F2F2F7; border-radius: 8px; border: 1px solid #E5E5EA;")
        p_lay = QVBoxLayout(p_frame) # 改为垂直布局，放两个数值
        p_lay.setSpacing(5)
        
        # 1. 算法处理后的值 (大字，蓝色) - 这是机器真正“看到”的值
        row1 = QHBoxLayout()
        row1.addWidget(QLabel("算法滤波值:"))
        self.lbl_filtered_p = QLabel("0.00 Bar")
        self.lbl_filtered_p.setStyleSheet("font-size: 26px; font-weight: bold; color: #007AFF;")
        self.lbl_filtered_p.setAlignment(Qt.AlignmentFlag.AlignRight)
        row1.addWidget(self.lbl_filtered_p)
        
        # 2. 原始瞬时值 (小字，灰色) - 这是含噪声的真实采样
        row2 = QHBoxLayout()
        lbl_raw_title = QLabel("原始瞬时值 (Raw):")
        lbl_raw_title.setStyleSheet("color: #8E8E93; font-size: 12px;")
        row2.addWidget(lbl_raw_title)
        
        self.lbl_raw_p = QLabel("0.00 Bar")
        self.lbl_raw_p.setStyleSheet("font-size: 14px; font-weight: normal; color: #FF3B30;") # 用红色显示跳动
        self.lbl_raw_p.setAlignment(Qt.AlignmentFlag.AlignRight)
        row2.addWidget(self.lbl_raw_p)

        p_lay.addLayout(row1)
        p_lay.addLayout(row2)
        layout.addWidget(p_frame)
        # ---------------------------

        grid = QGridLayout(); grid.setSpacing(10)
        for i in range(8):
            name = IDX_MAP.get(i, f"Line {i}")
            btn = QPushButton(f"{name}\nOFF")
            btn.setCheckable(True); btn.setFixedHeight(60)
            btn.setStyleSheet("background-color: #F2F2F7; color: #8E8E93; border: 1px solid #E5E5EA;")
            btn.clicked.connect(lambda chk, idx=i: self.toggle_line(idx))
            grid.addWidget(btn, i//2, i%2)
            self.buttons.append(btn)
        layout.addLayout(grid)

        # ... (后续按钮代码保持不变，省略以节省空间) ...
        # (请保留原有的 Run/Err/Pause 按钮组和关闭按钮)
        line = QFrame(); line.setFrameShape(QFrame.Shape.HLine); line.setStyleSheet("color: #E5E5EA;")
        layout.addWidget(line)
        lbl_ui = QLabel(f"运行状态")
        lbl_ui.setStyleSheet("font-weight: bold; color: #8E8E93;")
        layout.addWidget(lbl_ui)
        ui_box = QHBoxLayout()
        btn_run = QPushButton("运行(绿)"); btn_run.setStyleSheet("background-color: #34C759; color: white;")
        btn_run.clicked.connect(lambda: self.station.set_glow_state("run"))
        btn_err = QPushButton("报警(红)"); btn_err.setStyleSheet("background-color: #FF3B30; color: white;")
        btn_err.clicked.connect(self.manual_trigger_alarm)
        btn_pause = QPushButton("暂停(黄)"); btn_pause.setStyleSheet("background-color: #FF9500; color: white;")
        btn_pause.clicked.connect(lambda: self.station.set_glow_state("pause"))
        btn_idle = QPushButton("待机(灰)"); btn_idle.setStyleSheet("background-color: #8E8E93; color: white;")
        btn_idle.clicked.connect(lambda: self.station.set_glow_state("idle"))
        ui_box.addWidget(btn_run); ui_box.addWidget(btn_err); ui_box.addWidget(btn_pause); ui_box.addWidget(btn_idle)
        layout.addLayout(ui_box); layout.addStretch()
        close_btn = QPushButton("断开连接并关闭"); close_btn.setObjectName("BtnPrimary")
        close_btn.clicked.connect(self.accept)
        layout.addWidget(close_btn)


    def start_tasks(self):
        # ... (DO Task 部分保持不变) ...
        if not SIMULATION_MODE:
            try:
                self.do_task = nidaqmx.Task()
                lines = f"{self.dev_name}/port0/line{self.offset}:{self.offset+7}"
                self.do_task.do_channels.add_do_chan(lines, line_grouping=nidaqmx.constants.LineGrouping.CHAN_PER_LINE)
                self.do_task.start()
                self.do_task.write([False]*8)
            except Exception as e:
                QMessageBox.critical(self, "硬件错误 (DO)", f"无法占用DO通道:\n{e}")

            # [修改] AI Task 配置：增加缓冲，确保能读到多个点用于中值滤波
            try:
                self.ai_task = nidaqmx.Task()
                ai_idx = self.offset // 8
                ai_chan = f"{self.dev_name}/ai{ai_idx}"
                self.ai_task.ai_channels.add_ai_voltage_chan(
                    ai_chan, terminal_config=TerminalConfiguration.RSE, min_val=-10.0, max_val=10.0
                )
                # 配置采样时钟，确保有足够的点数
                self.ai_task.timing.cfg_samp_clk_timing(
                    rate=500, sample_mode=AcquisitionType.CONTINUOUS, samps_per_chan=1000
                )
                self.ai_task.start()
            except Exception as e:
                print(f"Warning: AI Task init failed in debug: {e}")
                self.ai_task = None

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_pressure)
        self.timer.start(100) # 10Hz 刷新率

    def update_pressure(self):
        """[核心修改] 同时显示原始值和经过中值+滑动平均处理后的值"""
        raw_val = 0.0
        filtered_val = 0.0
        
        if SIMULATION_MODE:
            # 仿真逻辑 (保持简单震荡)
            if self.current_states[3] and self.current_states[0]: self._sim_p += 0.2
            elif self.current_states[1] or self.current_states[2]: self._sim_p -= 0.3
            else: self._sim_p -= 0.05
            base_p = max(0, min(3.0, self._sim_p))
            
            # 模拟噪声：原始值乱跳，滤波值平滑
            noise = random.uniform(-0.15, 0.15) 
            raw_val = max(0, base_p + noise)
            
            self.debug_deque.append(raw_val) # 简化仿真，直接把带噪声的放进去
            filtered_val = sum(self.debug_deque) / len(self.debug_deque)
            
        elif self.ai_task:
            try:
                # 1. 读取缓冲区内所有数据 (10Hz刷新率下，500Hz采样率应该有50个点左右)
                data = self.ai_task.read(number_of_samples_per_channel=nidaqmx.constants.READ_ALL_AVAILABLE)
                
                if len(data) > 0:
                    # --- A. 计算原始瞬时值 (Raw) ---
                    # 为了展示效果，我们取最后一个点，或者如果有明显尖峰取最大值
                    # 这里取最后一个点作为“当前读数”
                    raw_volts = data[-1]
                    raw_val = max(0, (raw_volts - 1.0) * 2.5)
                    
                    # --- B. 计算算法处理值 (Filtered) ---
                    # 步骤1: 中值滤波 (去尖峰)
                    if len(data) >= 3:
                        median_volts = statistics.median(data)
                    else:
                        median_volts = sum(data)/len(data)
                    
                    mid_p = max(0, (median_volts - 1.0) * 2.5)
                    
                    # 步骤2: 滑动平均 (去抖动)
                    self.debug_deque.append(mid_p)
                    filtered_val = sum(self.debug_deque) / len(self.debug_deque)
                    if filtered_val < 0.05:
                        filtered_val = 0.0
                else:
                    # 没读到数据，保持上次的值
                    if self.debug_deque: filtered_val = self.debug_deque[-1]
                    
            except Exception:
                raw_val = 0.0
                filtered_val = 0.0
        
        # 更新 UI
        self.lbl_filtered_p.setText(f"{filtered_val:.2f} Bar")
        self.lbl_raw_p.setText(f"{raw_val:.2f} Bar")

    def manual_trigger_alarm(self):
        self.station.set_glow_state("error")
        if not SIMULATION_MODE and self.do_task:
            try:
                states = [False]*8; states[7] = True
                self.do_task.write(states)
                for i, btn in enumerate(self.buttons):
                    btn.setChecked(i==7)
                    self.update_btn_style(i, i==7)
            except Exception as e:
                QMessageBox.warning(self, "错误", f"硬件写入失败: {e}")

    def toggle_line(self, idx):
        is_on = self.buttons[idx].isChecked()
        self.current_states[idx] = is_on
        self.update_btn_style(idx, is_on)
        if not SIMULATION_MODE and self.do_task:
            try: self.do_task.write(self.current_states)
            except: pass
            
    def update_btn_style(self, idx, is_on):
        btn = self.buttons[idx]
        name = IDX_MAP.get(idx)
        if is_on:
            btn.setText(f"{name}\nON"); btn.setStyleSheet("background-color: #34C759; color: white; border: none;")
        else:
            btn.setText(f"{name}\nOFF"); btn.setStyleSheet("background-color: #F2F2F7; color: #8E8E93; border: 1px solid #E5E5EA;")

    def closeEvent(self, event):
        self.timer.stop()
        if self.do_task:
            try: self.do_task.write([False]*8); self.do_task.stop(); self.do_task.close()
            except: pass
        if self.ai_task:
            try: self.ai_task.stop(); self.ai_task.close()
            except: pass
        event.accept()


# ============================================================================
# [SECTION 5] 核心 UI 组件 (View Components)
# ============================================================================

class StationWidget(QFrame):
    sig_remove = pyqtSignal(object) # [New] 用于通知主窗口删除自己

    def __init__(self, idx, log_signal):
        super().__init__()
        self.setObjectName("Card") 
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.setMinimumHeight(480)
        
        self.idx = idx
        self.global_log = log_signal
        self.worker = None
        self.main_window = None
        self.hardware_connected = False
        self.data_x = []; self.data_y = []; self.start_time = 0
        self._ui_label_anim = QTimer(self)
        self._ui_label_anim.setInterval(80)
        self._ui_label_anim.timeout.connect(self._tick_value_labels)
        self._target_pressure = 0.0
        self._display_pressure = 0.0
        self._target_timer = None
        self._display_timer = None
        self._last_plot_update = 0.0
        self._button_anims = []
        self.init_ui()
        self.setup_breathing_animation()

    def setup_breathing_animation(self):
        self.glow_effect = QGraphicsDropShadowEffect(self)
        self.glow_effect.setBlurRadius(40); self.glow_effect.setYOffset(4)
        self.default_shadow_color = QColor(0, 0, 0, 25) 
        self.glow_effect.setColor(self.default_shadow_color)
        self.setGraphicsEffect(self.glow_effect)
        self.glow_anim = QPropertyAnimation(self.glow_effect, b"color")
        self.glow_anim.setDuration(1500); self.glow_anim.setLoopCount(-1)
        self.glow_anim.setEasingCurve(QEasingCurve.Type.InOutSine)

    def set_glow_state(self, state):
        self.glow_anim.stop()
        if state == "run": self._start_anim(QColor("#34C759"), 3000) 
        elif state == "error": self._start_anim(QColor("#FF3B30"), 800) 
        elif state == "pause": self._start_anim(QColor("#FF9500"), 2000) 
        else: self.glow_effect.setBlurRadius(40); self.glow_effect.setColor(self.default_shadow_color)

    def _start_anim(self, color, duration):
        start_c = QColor(color); start_c.setAlpha(40)
        end_c = QColor(color); end_c.setAlpha(220)
        self.glow_effect.setBlurRadius(60 if duration < 1000 else 40)
        self.glow_anim.setStartValue(start_c)
        self.glow_anim.setKeyValueAt(0.5, end_c)
        self.glow_anim.setEndValue(start_c)
        self.glow_anim.setDuration(duration)
        self.glow_anim.start()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(12); layout.setContentsMargins(24, 24, 24, 24)

        # Header
        h_lay = QHBoxLayout()
        self.lbl_title = QLabel(f"Station {self.idx}")
        self.lbl_title.setObjectName("CardTitle")
        
        self.lbl_status = QLabel("待机")
        self.lbl_status.setStyleSheet(STATUS_STYLES["stop"])
        
        # [New] 自由删除按钮
        self.btn_delete = QPushButton("✕")
        self.btn_delete.setObjectName("BtnDeleteCard")
        self.btn_delete.setFixedSize(30, 30)
        self.btn_delete.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_delete.clicked.connect(lambda: self.sig_remove.emit(self))
        
        h_lay.addWidget(self.lbl_title); h_lay.addStretch(); h_lay.addWidget(self.lbl_status)
        h_lay.addSpacing(15); h_lay.addWidget(self.btn_delete) # 添加删除按钮
        layout.addLayout(h_lay)

        # Config
        c_lay = QHBoxLayout()
        self.in_dev = QLineEdit("Dev1"); self.in_dev.setPlaceholderText("Device"); self.in_dev.setFixedWidth(70)
        self.combo_group = QComboBox()
        self.combo_group.addItems([f"Group {i} ({i*8}-{i*8+7})" for i in range(4)])
        self.combo_group.setCurrentIndex((self.idx - 1) % 4)
        self.btn_connect = QPushButton("连接"); self.btn_connect.setObjectName("BtnSecondary")
        self.btn_connect.setCheckable(True); self.btn_connect.setFixedWidth(70)
        self.btn_connect.clicked.connect(self.toggle_connection)
        c_lay.addWidget(QLabel("设备:")); c_lay.addWidget(self.in_dev)
        c_lay.addWidget(self.combo_group); c_lay.addWidget(self.btn_connect)
        layout.addLayout(c_lay)

        # Params
        p_lay = QGridLayout(); p_lay.setSpacing(10)
        self.in_cycles = QLineEdit("350")
        self.in_target = QLineEdit("2.02")
        self.in_floor = QLineEdit("0.02")
        self.in_max = QLineEdit("2.5"); self.in_max.setStyleSheet("color: #FF3B30; font-weight: bold;") 
        p_lay.addWidget(QLabel("目标循环:"),0,0); p_lay.addWidget(self.in_cycles,0,1)
        p_lay.addWidget(QLabel("高压 (Bar):"),0,2); p_lay.addWidget(self.in_target,0,3)
        p_lay.addWidget(QLabel("低压 (Bar):"),1,0); p_lay.addWidget(self.in_floor,1,1)
        p_lay.addWidget(QLabel("保护上限:"),1,2); p_lay.addWidget(self.in_max,1,3)
        layout.addLayout(p_lay)

        # Chart
        self.plot = pg.PlotWidget(); self.plot.setBackground('#FFFFFF'); self.plot.setMinimumHeight(160)
        self.plot.getAxis('left').setPen('#8E8E93'); self.plot.getAxis('bottom').setPen('#8E8E93')
        self.plot.setClipToView(True)
        self.plot.setDownsampling(mode='peak')
        self.plot.showGrid(x=True, y=True, alpha=0.15)
        self.curve = self.plot.plot(pen=pg.mkPen('#007AFF', width=2)) 
        layout.addWidget(self.plot)

        # Info Panel
        i_lay = QHBoxLayout()
        v_time = QVBoxLayout()
        self.lbl_timer = QLabel("--"); self.lbl_timer.setStyleSheet("font-size: 22px; font-weight: bold; color: #FF9500;")
        lbl_t = QLabel("倒计时 (s)"); lbl_t.setProperty("class", "SubLabel")
        v_time.addWidget(lbl_t); v_time.addWidget(self.lbl_timer)
        
        v_prog = QVBoxLayout(); v_prog.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_progress_val = QLabel("0 / 350"); self.lbl_progress_val.setStyleSheet("font-size: 22px; font-weight: bold; color: #1C1C1E;")
        lbl_prog = QLabel("循环进度"); lbl_prog.setProperty("class", "SubLabel")
        v_prog.addWidget(lbl_prog); v_prog.addWidget(self.lbl_progress_val)
        
        v_pres = QVBoxLayout(); v_pres.setAlignment(Qt.AlignmentFlag.AlignRight)
        self.lbl_pressure = QLabel("0.00"); self.lbl_pressure.setStyleSheet("font-size: 28px; font-weight: 700; color: #007AFF;")
        self.lbl_pressure.setAlignment(Qt.AlignmentFlag.AlignRight)
        lbl_p_t = QLabel("压力 (Bar)"); lbl_p_t.setProperty("class", "SubLabel"); lbl_p_t.setAlignment(Qt.AlignmentFlag.AlignRight)
        v_pres.addWidget(lbl_p_t); v_pres.addWidget(self.lbl_pressure)
        
        i_lay.addLayout(v_time); i_lay.addStretch(); i_lay.addLayout(v_prog); i_lay.addStretch(); i_lay.addLayout(v_pres)
        layout.addLayout(i_lay); layout.addStretch()

        # Buttons
        b_lay = QHBoxLayout()
        self.btn_manual = QPushButton("调试"); self.btn_manual.setObjectName("BtnSecondary")
        self.btn_manual.clicked.connect(self.open_manual)
        
        self.btn_start = QPushButton("开始测试"); self.btn_start.setObjectName("BtnPrimary"); self.btn_start.setEnabled(False)
        self.btn_start.clicked.connect(self.start_test)
        
        self.btn_stop = QPushButton("紧急停止"); self.btn_stop.setObjectName("BtnDanger"); self.btn_stop.setEnabled(False)
        self.btn_stop.clicked.connect(self.stop_test)
        
        b_lay.addWidget(self.btn_manual); b_lay.addWidget(self.btn_start, stretch=2); b_lay.addWidget(self.btn_stop)
        layout.addLayout(b_lay)

    def _animate_button_feedback(self, btn):
        if not btn.isVisible():
            return
        rect = btn.geometry()
        if rect.width() < 8 or rect.height() < 8:
            return
        inset = 2
        mid = QRect(rect.x() + inset, rect.y() + inset, rect.width() - inset * 2, rect.height() - inset * 2)
        anim = QPropertyAnimation(btn, b"geometry", self)
        anim.setDuration(160)
        anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        anim.setStartValue(rect)
        anim.setKeyValueAt(0.5, mid)
        anim.setEndValue(rect)
        anim.finished.connect(lambda a=anim: self._button_anims.remove(a) if a in self._button_anims else None)
        self._button_anims.append(anim)
        anim.start()

    def _tick_value_labels(self):
        p_diff = self._target_pressure - self._display_pressure
        if abs(p_diff) < 0.01:
            self._display_pressure = self._target_pressure
        else:
            self._display_pressure += p_diff * 0.35
        self.lbl_pressure.setText(f"{self._display_pressure:.2f}")

        if self._target_timer is not None:
            if self._display_timer is None:
                self._display_timer = self._target_timer
            t_diff = self._target_timer - self._display_timer
            if abs(t_diff) < 0.05:
                self._display_timer = self._target_timer
            else:
                self._display_timer += t_diff * 0.45
            self.lbl_timer.setText(f"{max(0.0, self._display_timer):.1f}")
        elif self.lbl_timer.text() != "--":
            self.lbl_timer.setText("--")

        if not (self.worker and self.worker.isRunning()) and self._target_timer is None:
            self._ui_label_anim.stop()

    def toggle_connection(self):
        if self.btn_connect.isChecked():
            dev_name = self.in_dev.text()
            offset = self.combo_group.currentIndex() * 8
            if self.main_window and self.main_window.is_channel_in_use(self, dev_name, offset):
                QMessageBox.warning(self, "连接冲突", f"{dev_name} Group {offset//8} 已被其他台架占用。")
                self.btn_connect.setChecked(False)
                return
            if not SIMULATION_MODE:
                try:
                    with nidaqmx.Task() as t:
                        t.do_channels.add_do_chan(f"{dev_name}/port0/line{offset}:{offset+7}", line_grouping=LineGrouping.CHAN_PER_LINE)
                except Exception as e:
                    QMessageBox.warning(self, "连接失败", f"无法连接到硬件:\n{e}")
                    self.btn_connect.setChecked(False); return
            
            self.hardware_connected = True
            self.in_dev.setEnabled(False); self.combo_group.setEnabled(False)
            self.btn_connect.setText("已连接"); self.btn_connect.setObjectName("BtnSuccess"); self.btn_connect.setStyleSheet("")
            self._animate_button_feedback(self.btn_connect)
            self.btn_start.setEnabled(True) 
            self.global_log.emit(f"[Station {self.idx}] 硬件已连接")
        else:
            self.hardware_connected = False
            self.in_dev.setEnabled(True); self.combo_group.setEnabled(True)
            self.btn_connect.setText("连接"); self.btn_connect.setObjectName("BtnSecondary"); self.btn_connect.setStyleSheet("")
            self._animate_button_feedback(self.btn_connect)
            self.btn_start.setEnabled(False)
            self.global_log.emit(f"[Station {self.idx}] 硬件断开")

    def _build_worker_config(self):
        dev_name = self.in_dev.text().strip()
        if not dev_name:
            raise ValueError("设备名称不能为空。")

        try:
            cycles = int(self.in_cycles.text().strip())
        except ValueError:
            raise ValueError("目标循环必须是整数。")

        try:
            target_p = float(self.in_target.text().strip())
            floor_p = float(self.in_floor.text().strip())
            max_p = float(self.in_max.text().strip())
        except ValueError:
            raise ValueError("压力参数必须是数字。")

        if cycles <= 0:
            raise ValueError("目标循环必须大于 0。")
        if floor_p < 0:
            raise ValueError("低压阈值不能小于 0。")
        if target_p <= floor_p:
            raise ValueError("高压阈值必须大于低压阈值。")
        if max_p <= target_p:
            raise ValueError("保护上限必须大于高压阈值。")

        return {
            'device': dev_name,
            'cycles': cycles,
            'target_p': target_p,
            'floor_p': floor_p,
            'max_p': max_p,
            'simulation': SIMULATION_MODE,
            'station_idx': self.idx
        }

    def start_test(self):
        if not self.hardware_connected and not SIMULATION_MODE:
            QMessageBox.warning(self, "未连接", "请先点击'连接'按钮锁定硬件配置。")
            return

        if self.worker and self.worker.isRunning():
            self.toggle_pause()
            return

        offset = self.combo_group.currentIndex() * 8
        try:
            cfg = self._build_worker_config()
        except ValueError as e:
            QMessageBox.warning(self, "参数错误", str(e))
            return
        
        self.data_x = []; self.data_y = []; self.curve.setData([], [])
        self.start_time = time.time()
        self._last_plot_update = 0.0
        self._target_pressure = 0.0
        self._display_pressure = 0.0
        self._target_timer = None
        self._display_timer = None
        self.lbl_pressure.setText("0.00")
        self.lbl_timer.setText("--")
        self.lbl_progress_val.setText(f"0 / {cfg['cycles']}") 
        
        try:
            log_dir = self.main_window.log_dir if (self.main_window and hasattr(self.main_window, "log_dir")) else os.getcwd()
            self.worker = TestWorker(cfg, offset, log_dir)
        except ValueError as e:
            QMessageBox.critical(self, "启动失败", str(e))
            return
        self.worker.sig_pressure.connect(self.update_gui_data)
        self.worker.sig_timer.connect(self.update_timer)
        self.worker.sig_status.connect(self.update_status)
        self.worker.sig_progress.connect(self.update_progress)
        self.worker.sig_log.connect(lambda m: self.global_log.emit(f"[Station {self.idx}] {m}"))
        self.worker.sig_finished.connect(self.on_finish)
        self.worker.sig_error.connect(self.on_error)
        self.worker.sig_button_update.connect(self.update_start_btn_text) 
        
        self.btn_start.setText("暂停测试")
        self.btn_start.setStyleSheet("background-color: #FF9500; color: white; border: none;") 
        self._animate_button_feedback(self.btn_start)
        self.btn_manual.setEnabled(False); self.btn_connect.setEnabled(False); self.btn_stop.setEnabled(True)
        # [New] 运行时禁用删除按钮，防止误操作
        self.btn_delete.setVisible(False)
        
        self.set_glow_state("run")
        if not self._ui_label_anim.isActive():
            self._ui_label_anim.start()
        self.worker.start()

    def toggle_pause(self):
        if not self.worker: return
        
        if self.worker.is_paused:
            self.worker.set_pause(False)
            self.btn_start.setText("暂停测试")
            self.btn_start.setStyleSheet("background-color: #FF9500; color: white; border: none;")
            self._animate_button_feedback(self.btn_start)
            self.set_glow_state("run")
        else:
            self.worker.set_pause(True)
            self.btn_start.setText("继续测试")
            self.btn_start.setStyleSheet("background-color: #34C759; color: white; border: none;")
            self._animate_button_feedback(self.btn_start)
            self.set_glow_state("pause")

    def update_start_btn_text(self, mode):
        if mode == "continue":
            self.btn_start.setText("继续测试")
            self.btn_start.setStyleSheet("background-color: #34C759; color: white; border: none;")
            self._animate_button_feedback(self.btn_start)
            self.set_glow_state("error") 

    def open_manual(self):
        ManualControlDialog(self.in_dev.text(), self.combo_group.currentIndex() * 8, self, self).exec()

    def stop_test(self):
        if self.worker: self.worker.stop()

    def update_gui_data(self, val):
        self._target_pressure = val
        if not self._ui_label_anim.isActive():
            self._ui_label_anim.start()
        now = time.time()
        self.data_x.append(now - self.start_time); self.data_y.append(val)
        if len(self.data_x) > 1000: self.data_x.pop(0); self.data_y.pop(0)
        if (now - self._last_plot_update) >= 0.1:
            self.curve.setData(self.data_x, self.data_y)
            self._last_plot_update = now

    def update_timer(self, text):
        if text == "--":
            self._target_timer = None
            self._display_timer = None
            self.lbl_timer.setText("--")
            return
        try:
            self._target_timer = max(0.0, float(text))
        except ValueError:
            self.lbl_timer.setText(text)
            return
        if self._display_timer is None:
            self._display_timer = self._target_timer
        if not self._ui_label_anim.isActive():
            self._ui_label_anim.start()

    def update_status(self, msg, style):
        self.lbl_status.setText(msg); self.lbl_status.setStyleSheet(style)

    def update_progress(self, current):
        self.lbl_progress_val.setText(f"{current} / {self.in_cycles.text()}")

    def on_error(self, err_msg):
        self.set_glow_state("error")
        self.global_log.emit(f"[Station {self.idx} 故障] {err_msg}")

    def on_finish(self):
        self.btn_start.setText("开始测试")
        self.btn_start.setObjectName("BtnPrimary"); self.btn_start.setStyleSheet("") 
        self.btn_start.setEnabled(True); self.btn_manual.setEnabled(True); self.btn_connect.setEnabled(True); self.btn_stop.setEnabled(False)
        # [New] 测试结束后重新显示删除按钮
        self.btn_delete.setVisible(True)
        
        self.lbl_timer.setText("--")
        self._target_timer = None
        self._display_timer = None
        self._target_pressure = self._display_pressure
        txt = self.lbl_status.text()
        self.set_glow_state("error" if "故障" in txt or "急停" in txt else "idle")


# ============================================================================
# [SECTION 6] 主窗口 (Main Application Window)
# ============================================================================

class MainWindow(QMainWindow):
    sig_log = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self.setWindowTitle(f"Compressor Lifetime Rev1.0")
        self.resize(1440, 960)
        self.stations = []
        self._entry_anims = []
        self._settings_expanded = True
        self._settings_target_height = 60
        self.settings_store = QSettings("FMC", "CompressorLifetime")
        saved_dir = str(self.settings_store.value("log_dir", os.getcwd()))
        self.log_dir = saved_dir if os.path.isdir(saved_dir) else os.getcwd()
        
        # 主布局
        main_w = QWidget(); main_w.setObjectName("CentralWidget")
        self.setCentralWidget(main_w)
        layout = QVBoxLayout(main_w); layout.setSpacing(0); layout.setContentsMargins(0,0,0,0)

        # Top Bar
        top_bar = QFrame()
        top_bar.setStyleSheet("background-color: #F9F9F9; border-bottom: 1px solid #E5E5EA;")
        top_bar.setFixedHeight(40)
        tb_layout = QHBoxLayout(top_bar); tb_layout.setContentsMargins(10,0,10,0)
        self.btn_toggle = QPushButton("⚙️ 系统设置 (System Settings) ▼")
        self.btn_toggle.setObjectName("BtnToggleSettings")
        self.btn_toggle.clicked.connect(self.toggle_settings)
        tb_layout.addWidget(self.btn_toggle); tb_layout.addStretch()
        layout.addWidget(top_bar)

        # Settings Panel
        self.settings_panel = QFrame()
        self.settings_panel.setObjectName("SettingsPanel")
        self.settings_panel.setMinimumHeight(0)
        self.settings_panel.setMaximumHeight(self._settings_target_height)
        sp_layout = QHBoxLayout(self.settings_panel); sp_layout.setContentsMargins(20, 0, 20, 0)
        
        self.btn_add = QPushButton(" + 增加台架 ")
        self.btn_add.setObjectName("BtnAdd")
        self.btn_add.setFixedSize(100, 36)
        self.btn_add.clicked.connect(self.add_station)
        
        # [Modified] 移除了全局删除按钮，因为现在可以在每个台架上独立删除
        
        self.chk_sim = QCheckBox("仿真模式 (Simulation)")
        self.chk_sim.setStyleSheet("font-weight: bold; color: #007AFF;")
        self.chk_sim.stateChanged.connect(self.toggle_sim)
        
        self.lbl_dir = QLabel(self.log_dir)
        self.lbl_dir.setStyleSheet("color: #8E8E93;")
        
        btn_dir = QPushButton("更改路径")
        btn_dir.setObjectName("BtnSecondary")
        btn_dir.setFixedSize(100, 36)
        btn_dir.clicked.connect(self.set_dir)
        
        sp_layout.addWidget(self.btn_add)
        line = QFrame(); line.setFrameShape(QFrame.Shape.VLine); line.setStyleSheet("color: #E5E5EA;")
        sp_layout.addWidget(line)
        sp_layout.addWidget(self.chk_sim); sp_layout.addStretch()
        sp_layout.addWidget(self.lbl_dir); sp_layout.addWidget(btn_dir)
        layout.addWidget(self.settings_panel)
        self.settings_anim = QPropertyAnimation(self.settings_panel, b"maximumHeight", self)
        self.settings_anim.setDuration(240)
        self.settings_anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        self.settings_anim.finished.connect(self._on_settings_anim_finished)

        # Content Splitter
        self.splitter = QSplitter(Qt.Orientation.Vertical)
        self.splitter.setHandleWidth(8); self.splitter.setChildrenCollapsible(False)
        
        # Scroll Area
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        grid_w = QWidget(); grid_w.setObjectName("ScrollContents")
        self.grid = QGridLayout(grid_w); self.grid.setSpacing(20); self.grid.setContentsMargins(20, 20, 20, 20)
        scroll.setWidget(grid_w); self.splitter.addWidget(scroll)

        # Log Area
        log_cont = QFrame(); log_cont.setObjectName("LogContainer")
        log_lay = QVBoxLayout(log_cont); log_lay.setContentsMargins(10, 10, 10, 10)
        lbl_log = QLabel("System Log")
        lbl_log.setStyleSheet("color: #8E8E93; font-weight: bold; font-size: 12px;")
        log_lay.addWidget(lbl_log)
        self.log = QTextEdit(); self.log.setReadOnly(True)
        log_lay.addWidget(self.log)
        self.splitter.addWidget(log_cont); self.splitter.setSizes([800, 200])
        
        layout.addWidget(self.splitter)
        self.sig_log.connect(self.append_log)
        
        set_keep_awake(True)
        self.add_station() 

    def add_station(self):
        # 寻找一个新的可用ID（不一定是连续的，但用于标识）
        existing_ids = [s.idx for s in self.stations]
        new_idx = 1
        while new_idx in existing_ids:
            new_idx += 1
            
        st = StationWidget(new_idx, self.sig_log)
        st.main_window = self
        st.sig_remove.connect(self.delete_specific_station) # [New] 绑定删除信号
        self.stations.append(st)
        self.rearrange_layout(animate=ENABLE_ENTRY_ANIMATION)
        self.append_log(f"系统: 已增加台架 (ID: {new_idx})")

    def is_channel_in_use(self, requester, dev_name, offset):
        for st in self.stations:
            if st is requester:
                continue
            if not st.hardware_connected:
                continue
            same_device = st.in_dev.text().strip() == dev_name.strip()
            same_offset = (st.combo_group.currentIndex() * 8) == offset
            if same_device and same_offset:
                return True
        return False

    def delete_specific_station(self, station_widget):
        """[New] 删除指定的台架"""
        if len(self.stations) <= 1:
            QMessageBox.warning(self, "操作无效", "系统至少需要保留一个台架。")
            return
            
        if station_widget.worker and station_widget.worker.isRunning():
            QMessageBox.critical(self, "禁止删除", f"台架 {station_widget.idx} 正在运行中，请先停止测试后再删除。")
            return

        # 移除流程
        idx = station_widget.idx
        self.stations.remove(station_widget) # 从列表移除
        self.grid.removeWidget(station_widget) # 从布局移除
        station_widget.deleteLater() # 销毁对象
        
        self.rearrange_layout() # 重新排布
        self.append_log(f"系统: 已移除台架 (ID: {idx})")

    def rearrange_layout(self, animate=False):
        # 先临时移除所有
        for i in reversed(range(self.grid.count())):
            w = self.grid.itemAt(i).widget()
            if w: w.setParent(None)
            
        count = len(self.stations)
        cols = 1 if count == 1 else (2 if count <= 4 else 3) # 动态列数
        
        # 重置拉伸因子
        for i in range(20): self.grid.setColumnStretch(i, 0); self.grid.setRowStretch(i, 0)
        for c in range(cols): self.grid.setColumnStretch(c, 1)
        for r in range((count + cols - 1) // cols): self.grid.setRowStretch(r, 1)

        # 重新添加
        for i, st in enumerate(self.stations):
            self.grid.addWidget(st, i // cols, i % cols)
            st.setVisible(True)
            if animate:
                self._animate_station_entry(st, i)

    def _animate_station_entry(self, station, order):
        if not ENABLE_ENTRY_ANIMATION:
            return
        # 当前默认关闭卡片入场动画，优先保证布局稳定、避免抖动。
        # 若后续要恢复，建议使用不影响 layout 的轻量效果（例如仅内容渐变）。

    def toggle_settings(self):
        self.settings_anim.stop()
        if self._settings_expanded:
            self._settings_expanded = False
            self.settings_anim.setStartValue(self.settings_panel.maximumHeight())
            self.settings_anim.setEndValue(0)
        else:
            self._settings_expanded = True
            self.settings_panel.setVisible(True)
            self.settings_anim.setStartValue(self.settings_panel.maximumHeight())
            self.settings_anim.setEndValue(self._settings_target_height)
        self.settings_anim.start()
        self.btn_toggle.setText("⚙️ 系统设置 (System Settings) " + ("▼" if self._settings_expanded else "▶"))

    def _on_settings_anim_finished(self):
        if not self._settings_expanded:
            self.settings_panel.setVisible(False)

    def toggle_sim(self, s):
        global SIMULATION_MODE
        if any(st.worker and st.worker.isRunning() for st in self.stations):
            QMessageBox.warning(self, "操作受限", "有台架正在运行，不能切换仿真模式。")
            self.chk_sim.blockSignals(True)
            self.chk_sim.setChecked(SIMULATION_MODE)
            self.chk_sim.blockSignals(False)
            return
        SIMULATION_MODE = (s == 2)
        self.append_log(f"系统模式切换: {'仿真' if SIMULATION_MODE else '硬件'}")

    def set_dir(self):
        d = QFileDialog.getExistingDirectory()
        if d:
            self.log_dir = d
            self.lbl_dir.setText(d)
            self.settings_store.setValue("log_dir", d)

    def append_log(self, t):
        self.log.append(f"[{datetime.now().strftime('%H:%M:%S')}] {t}")
        self.log.verticalScrollBar().setValue(self.log.verticalScrollBar().maximum())

    def closeEvent(self, event):
        set_keep_awake(False)
        for s in self.stations:
            if s.worker and s.worker.isRunning():
                s.stop_test()
        for s in self.stations:
            if s.worker and s.worker.isRunning():
                s.worker.wait(3000)
        event.accept()


# ============================================================================
# [SECTION 7] 程序入口 (Entry Point)
# ============================================================================

if __name__ == '__main__':
    # 高分屏适配
    os.environ["QT_SCALE_FACTOR"] = "1"
    if hasattr(Qt.ApplicationAttribute, 'AA_EnableHighDpiScaling'): 
        QApplication.setAttribute(Qt.ApplicationAttribute.AA_EnableHighDpiScaling, True)
    
    app = QApplication(sys.argv)
    
    # 设置全局字体与主题
    app.setStyleSheet(IOS_LIGHT_THEME)
    app.setFont(QFont("Segoe UI", 9))
    
    w = MainWindow()
    w.showMaximized()
    sys.exit(app.exec())
