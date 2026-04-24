# -*- coding: utf-8 -*-
"""
==============================================================================
项目名称 (Project)   : Compressor Lifetime Test System (压缩机寿命耐久测试系统)
文件名称 (Filename)  : compressor_lifetime_2_1.py
版本号   (Version)   : Rev 3.0 
作者     (Author)    : [Zhang zhelei/ Michelin]
所属机构 (Company)   : [Fresenius Medical Care / VTC]
修改日期 (Date)      : 2025-11-18
版权声明 (Copyright) : Copyright (C) 2025 [Fresenius Medical Care]. All Rights Reserved.

功能描述 (Description):
    程序用于控制NI USB-6362/6363数据采集卡，对压缩机进行自动化的寿命测试。
    
    [Rev 3.0 新增功能]:
    1. 暂停/继续控制：在测试过程中可随时暂停，并在暂停期间强制关闭压缩机。
    2. 故障恢复：故障触发后进入暂停状态，允许用户检查后点击“继续”恢复测试。
    3. 视觉优化：新增暂停状态的黄色呼吸灯效果。
    4. 按钮交互：开始按钮动态切换为“暂停测试”或“继续测试”。

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

# --- 2. 第三方库导入 (GUI & Plotting) ---
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QGridLayout, QLabel, 
                             QLineEdit, QPushButton, QCheckBox, QTextEdit, 
                             QFileDialog, QSplitter, QMessageBox,
                             QScrollArea, QDialog, QComboBox,
                             QSizePolicy, QFrame, QGraphicsDropShadowEffect)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QPropertyAnimation, QEasingCurve
from PyQt6.QtGui import QFont, QColor, QPalette

import pyqtgraph as pg

# --- 3. 硬件驱动导入 (NI-DAQmx) ---
import nidaqmx
from nidaqmx.constants import LineGrouping, TerminalConfiguration


# ============================================================================
# [SECTION 1] 全局配置与样式 (Global Configuration)
# ============================================================================

IDX_MAP = {
    0: "V1 阀门", 1: "V2 阀门", 2: "V3 阀门", 3: "压缩机",
    4: "压力计供电", 5: "计数供电", 6: "计数信号", 7: "蜂鸣器/报警"
}

SIMULATION_MODE = False  

STATUS_STYLES = {
    "run": "color: #34C759; font-weight: bold; font-size: 15px; background-color: transparent;",
    "stop": "color: #8E8E93; font-weight: bold; font-size: 15px; background-color: transparent;",
    "err": "color: #FF3B30; font-weight: bold; font-size: 15px; background-color: transparent;",
    "pause": "color: #FF9500; font-weight: bold; font-size: 15px; background-color: transparent;", # [New] 黄色
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
    QPushButton#BtnRemove { background-color: #FFEBEE; color: #C62828; border: 1px solid #FFCDD2; }
    
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

# ============================================================================
# [SECTION 3] 核心逻辑层 (Core Logic / Backend)
# ============================================================================

# [New] 定义一个用于控制“重跑当前循环”的自定义异常
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
        self.dev_name = config['device']
        self.target_cycles = int(config['cycles'])
        self.target_p = float(config['target_p'])
        self.floor_p = float(config['floor_p'])
        self.max_p = float(config['max_p'])
        self.sim_mode = config['simulation']
        self._sim_p_val = 0.0
        self._last_pressure = 0.0 
        self._first_read = True 
        self.step_max_p = 0.0
        self.step_min_p = 99.9  
        self.fault_triggered = False
        self.last_do_states = [False] * 8

    def run(self):
        try:
            self.setup_hardware()
            self.create_log_file()
            self.sig_log.emit(f"启动: {self.dev_name} [Line {self.offset}-{self.offset+7}]")

            # [Modify] 将 for 循环改为 while 循环，以便控制循环索引不自增（实现重跑）
            current_cycle = 1
            while current_cycle <= self.target_cycles:
                if not self.is_running: break

                try:
                    # 1. 正常流程
                    self.check_pause_state() # 循环开始前的检查

                    self.sig_status.emit(f"循环 {current_cycle}: 启动", STATUS_STYLES["run"])
                    
                    # 运行阶段 1
                    if not self.run_phase_1(current_cycle): 
                        if not self.is_running: break # 如果是用户停止，直接退出
                        # 如果是Phase1内部故障触发了Retry，会被下方except捕获，不会走到这里

                    # 运行阶段 2
                    if not self.run_phase_2(current_cycle):
                        if not self.is_running: break

                    # 计数器动作
                    self.sig_status.emit(f"循环 {current_cycle}: 计数器触发", STATUS_STYLES["run"])
                    self._trigger_counter()
                    
                    if not self.sleep_smart(1.0): break
                    
                    # 成功完成本轮，进度+1
                    self.sig_progress.emit(current_cycle)
                    current_cycle += 1
                
                except RetryCycleError:
                    # [New] 捕获到了重试信号
                    if not self.is_running: break
                    self.sig_log.emit(f"警告: 第 {current_cycle} 次循环发生故障，系统复位并重跑当前循环...")
                    self.sig_status.emit(f"正在复位循环 {current_cycle}...", STATUS_STYLES["run"])
                    
                    # 复位硬件状态，准备重跑
                    self.finalize_success() # 简单复位所有阀门
                    time.sleep(2.0) # 稍作停顿给硬件缓冲
                    
                    # 注意：这里不执行 current_cycle += 1，下一次 while 循环依然跑当前的 cycle
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
        """
        普通暂停：原地等待，恢复后继续。
        故障暂停：等待确认，恢复后抛出 RetryCycleError。
        """
        if self.is_paused and self.is_running:
            self.sig_status.emit("已暂停 / 等待恢复", STATUS_STYLES["pause"])
            
            # 硬件安全动作
            temp_safe_states = list(self.last_do_states)
            temp_safe_states[3] = False # 关压缩机
            if self.fault_triggered:
                temp_safe_states[7] = True # 故障时开蜂鸣器
                self.sig_log.emit(f"故障暂停: 等待用户操作 (复位模式)")
            else:
                self.sig_log.emit(f"手动暂停: 保持状态 (继续模式)")
            
            if not self.sim_mode and self.do_task:
                try: self.do_task.write(temp_safe_states)
                except: pass
            
            # 阻塞等待
            while self.is_paused and self.is_running:
                time.sleep(0.1)
                self.read_pressure(silent=True)

            # 恢复逻辑
            if self.is_running:
                if self.fault_triggered:
                    # [New] 如果是故障导致的暂停，清除故障标记，并抛出异常请求重跑
                    self.fault_triggered = False 
                    raise RetryCycleError()
                else:
                    # 如果是手动暂停，恢复硬件状态，原地继续
                    self.sig_status.emit("恢复运行...", STATUS_STYLES["run"])
                    self.sig_log.emit("手动暂停结束，继续执行剩余步骤")
                    self.write_do(self.last_do_states)

    def trigger_fault(self, error_msg):
        """
        触发故障 -> 暂停 -> 用户点击继续 -> 抛出异常 -> 主循环捕获 -> 重跑
        """
        self.fault_triggered = True
        self.is_paused = True
        self.sig_error.emit(error_msg)
        self.sig_button_update.emit("continue")
        
        # 这里调用 check_pause_state 会进入阻塞。
        # 当用户点击继续，check_pause_state 会在内部抛出 RetryCycleError。
        # 所以这里不需要额外的逻辑，异常会自动向上传递给 run_phase_X，最终被 run() 捕获。
        self.check_pause_state()

    # --- 以下方法与 Rev 2.1 保持一致，无需修改 ---
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
                rate=500, sample_mode=nidaqmx.constants.AcquisitionType.CONTINUOUS, samps_per_chan=1000
            )
            self.ai_task.start()
        except Exception as e:
            self.ai_task.close()
            self.do_task.close()
            raise RuntimeError(f"AI初始化失败: {e}")

    def read_pressure(self, silent=False):
        if self.sim_mode: return self._simulate_pressure(silent)
        try:
            data = self.ai_task.read(number_of_samples_per_channel=nidaqmx.constants.READ_ALL_AVAILABLE)
            if len(data) > 0: avg_volts = sum(data) / len(data)
            else: return self._last_pressure 
            current_p = max(0, (avg_volts - 1.0) * 2.5)
            alpha = 0.8 
            if self._first_read: self._last_pressure = current_p; self._first_read = False
            filtered_p = alpha * current_p + (1 - alpha) * self._last_pressure
            self._last_pressure = filtered_p 
            if not silent: self.sig_pressure.emit(filtered_p)
            self._update_stats(filtered_p)
            self._check_safety(filtered_p)
            return filtered_p
        except Exception as e:
            if self.is_running: raise e
            return 0.0

    def write_do(self, states):
        if not self.is_running: return
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
            try: self.do_task.stop(); self.do_task.start(); self.do_task.write([False]*8)
            except: pass

    def run_phase_1(self, cycle):
        success_count = 0 
        for i in range(4):
            self.check_pause_state() 
            self.step_max_p = 0.0; self.step_min_p = 99.9
            if not self.is_running: return False
            self.sig_status.emit(f"P1 ({i+1}/4): 初始加压", STATUS_STYLES["run"])
            current_loop_reached = False; in_release_mode = False; t_start = time.time()
            while time.time() - t_start < 90.0:
                if not self.is_running: return False
                
                if self.is_paused: self.check_pause_state() 
                
                self.sig_timer.emit(f"{90.0 - (time.time() - t_start):.1f}")
                p = self.read_pressure()
                states = [False]*8; states[0]=True; states[4]=True; states[5]=True 
                if not in_release_mode:
                    states[3] = True 
                    if p >= self.target_p:
                        current_loop_reached = True; in_release_mode = True
                        states[3]=True; states[1]=True; states[2]=True; states[0]=False
                        self.sig_status.emit(f"P1 ({i+1}/4): 达标泄压", STATUS_STYLES["run"])
                else:
                    states[3]=True; states[1]=True; states[2]=True; states[0]=False
                    if p <= self.floor_p:
                        in_release_mode = False
                        self.sig_status.emit(f"P1 ({i+1}/4): 重新打压", STATUS_STYLES["run"])
                self.write_do(states); time.sleep(0.1)
            if current_loop_reached: success_count += 1
            else: self.sig_log.emit(f"警告: P1 第 {i+1} 次循环未达到目标压力")
            if not self.run_release_57s(cycle, f"P1 ({i+1}/4)"): return False
            self.log_csv(cycle, "Phase_1", f"{i+1}/4 Done", self.read_pressure(silent=True))
        if success_count == 0:
            self.trigger_fault(f"故障: 阶段一循环均未达到目标压力 {self.target_p} Bar")
            return False 
        return True

    def run_phase_2(self, cycle):
        for i in range(14):
            self.check_pause_state() 
            self.step_max_p = 0.0; self.step_min_p = 99.9
            if not self.is_running: return False
            for j in range(10):
                if not self.is_running: return False
                if self.is_paused: self.check_pause_state() 
                
                self.sig_status.emit(f"P2 ({i+1}/14): 脉冲 {j+1}/10", STATUS_STYLES["run"])
                if j == 9: self._run_complex_pulse()
                else: self._run_simple_pulse()
            if not self.run_release_57s(cycle, f"P2 ({i+1}/14)"): return False
            self.log_csv(cycle, "Phase_2", f"{i+1}/14 Done", self.read_pressure(silent=True))
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
        start = time.time()
        while time.time() - start < duration:
            if not self.is_running: return False
            if self.is_paused: self.check_pause_state() 
            self.sig_timer.emit(f"{duration - (time.time() - start):.1f}")
            self.read_pressure() 
            time.sleep(0.1)
        self.sig_timer.emit("0.0")
        return True

    def finalize_success(self):
        if self.sim_mode: return
        try:
            if self.do_task: f = [False]*8; f[4]=True; f[5]=True; self.do_task.write(f)
        except: pass

    def cleanup(self):
        if not self.sim_mode and self.do_task:
            try:
                states = [False]*8
                if self.fault_triggered: states[7] = True
                self.do_task.write(states); self.do_task.close()
            except: pass
        if not self.sim_mode and self.ai_task:
            try: self.ai_task.close()
            except: pass

    def create_log_file(self):
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.csv_file = os.path.join(self.log_dir, f"Log_{self.dev_name}_Grp{self.offset//8}_{ts}.csv")
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
        except: pass

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
        if val > self.max_p: self.trigger_fault(f"压力超限: {val:.2f} > {self.max_p}")

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
            self.write_do(s1); time.sleep(0.1)
            s2 = [False]*8; s2[0]=True; s2[3]=True; s2[4]=True; s2[5]=True
            self.write_do(s2); time.sleep(0.1)
        for _ in range(5): 
            if not self.is_running: return
            s3 = [False]*8; s3[0]=True; s3[2]=True; s3[4]=True; s3[5]=True
            self.write_do(s3); time.sleep(0.1)
            s4 = [False]*8; s4[0]=True; s4[4]=True; s4[5]=True
            self.write_do(s4); time.sleep(0.1)


# ============================================================================
# [SECTION 4] 辅助 UI 组件 (Dialogs)
# ============================================================================

class ManualControlDialog(QDialog):
    def __init__(self, dev_name, offset, station_widget, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"调试模式 (Debug) - {dev_name}")
        self.setFixedSize(460, 520)
        self.dev_name = dev_name; self.offset = offset
        self.station = station_widget; self.task = None
        self.current_states = [False] * 8; self.buttons = []
        self.init_ui()
        self.start_task()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(15); layout.setContentsMargins(20, 20, 20, 20)

        title = QLabel(f"IO Control: Line {self.offset} - {self.offset+7}")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet("font-size: 18px; font-weight: bold; color: #333;")
        layout.addWidget(title)

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

        line = QFrame(); line.setFrameShape(QFrame.Shape.HLine); line.setStyleSheet("color: #E5E5EA;")
        layout.addWidget(line)
        
        lbl_ui = QLabel(f"UI 效果测试 (呼吸灯)")
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

    def start_task(self):
        if SIMULATION_MODE: return
        try:
            self.task = nidaqmx.Task()
            lines = f"{self.dev_name}/port0/line{self.offset}:{self.offset+7}"
            self.task.do_channels.add_do_chan(lines, line_grouping=LineGrouping.CHAN_PER_LINE)
            self.task.start()
            self.task.write([False]*8)
        except Exception as e:
            QMessageBox.critical(self, "硬件错误", f"无法占用DO通道:\n{e}")
            self.close()

    def manual_trigger_alarm(self):
        self.station.set_glow_state("error")
        if not SIMULATION_MODE and self.task:
            try:
                states = [False]*8; states[7] = True
                self.task.write(states)
                for i, btn in enumerate(self.buttons):
                    btn.setChecked(i==7)
                    self.update_btn_style(i, i==7)
            except Exception as e:
                QMessageBox.warning(self, "错误", f"硬件写入失败: {e}")

    def toggle_line(self, idx):
        is_on = self.buttons[idx].isChecked()
        self.current_states[idx] = is_on
        self.update_btn_style(idx, is_on)
        if not SIMULATION_MODE and self.task:
            try: self.task.write(self.current_states)
            except: pass
            
    def update_btn_style(self, idx, is_on):
        btn = self.buttons[idx]
        name = IDX_MAP.get(idx)
        if is_on:
            btn.setText(f"{name}\nON"); btn.setStyleSheet("background-color: #34C759; color: white; border: none;")
        else:
            btn.setText(f"{name}\nOFF"); btn.setStyleSheet("background-color: #F2F2F7; color: #8E8E93; border: 1px solid #E5E5EA;")

    def closeEvent(self, event):
        if self.task:
            try: self.task.write([False]*8); self.task.stop(); self.task.close()
            except: pass
        event.accept()


# ============================================================================
# [SECTION 5] 核心 UI 组件 (View Components)
# ============================================================================

class StationWidget(QFrame):
    def __init__(self, idx, log_signal):
        super().__init__()
        self.setObjectName("Card") 
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.setMinimumHeight(480)
        
        self.idx = idx
        self.global_log = log_signal
        self.worker = None
        self.hardware_connected = False
        self.data_x = []; self.data_y = []; self.start_time = 0
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
        if state == "run": self._start_anim(QColor("#34C759"), 3000) # 绿
        elif state == "error": self._start_anim(QColor("#FF3B30"), 800) # 红
        elif state == "pause": self._start_anim(QColor("#FF9500"), 2000) # [New] 黄
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
        h_lay.addWidget(self.lbl_title); h_lay.addStretch(); h_lay.addWidget(self.lbl_status)
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
        self.lbl_progress_val = QLabel("0 / 10"); self.lbl_progress_val.setStyleSheet("font-size: 22px; font-weight: bold; color: #1C1C1E;")
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

    def toggle_connection(self):
        if self.btn_connect.isChecked():
            dev_name = self.in_dev.text()
            offset = self.combo_group.currentIndex() * 8
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
            self.btn_start.setEnabled(True) 
            self.global_log.emit(f"[Station {self.idx}] 硬件已连接")
        else:
            self.hardware_connected = False
            self.in_dev.setEnabled(True); self.combo_group.setEnabled(True)
            self.btn_connect.setText("连接"); self.btn_connect.setObjectName("BtnSecondary"); self.btn_connect.setStyleSheet("")
            self.btn_start.setEnabled(False)
            self.global_log.emit(f"[Station {self.idx}] 硬件断开")

    def start_test(self):
        if not self.hardware_connected and not SIMULATION_MODE:
            QMessageBox.warning(self, "未连接", "请先点击'连接'按钮锁定硬件配置。")
            return

        # [New] 如果 Worker 存在且运行中（包含暂停状态），则执行暂停/继续切换
        if self.worker and self.worker.isRunning():
            self.toggle_pause()
            return

        dev_name = self.in_dev.text()
        offset = self.combo_group.currentIndex() * 8
        cfg = {'device': dev_name, 'cycles': self.in_cycles.text(), 'target_p': self.in_target.text(),
               'floor_p': self.in_floor.text(), 'max_p': self.in_max.text(), 'simulation': SIMULATION_MODE}
        
        self.data_x = []; self.data_y = []; self.curve.setData([], [])
        self.start_time = time.time()
        self.lbl_progress_val.setText(f"0 / {cfg['cycles']}") 
        
        self.worker = TestWorker(cfg, offset, os.getcwd())
        self.worker.sig_pressure.connect(self.update_gui_data)
        self.worker.sig_timer.connect(self.lbl_timer.setText)
        self.worker.sig_status.connect(self.update_status)
        self.worker.sig_progress.connect(self.update_progress)
        self.worker.sig_log.connect(lambda m: self.global_log.emit(f"[Station {self.idx}] {m}"))
        self.worker.sig_finished.connect(self.on_finish)
        self.worker.sig_error.connect(self.on_error)
        self.worker.sig_button_update.connect(self.update_start_btn_text) # [New] 连接信号
        
        # 初始运行状态 UI
        self.btn_start.setText("暂停测试")
        self.btn_start.setStyleSheet("background-color: #FF9500; color: white; border: none;") # 设为黄色，点击即暂停
        self.btn_manual.setEnabled(False); self.btn_connect.setEnabled(False); self.btn_stop.setEnabled(True)
        
        self.set_glow_state("run")
        self.worker.start()

    def toggle_pause(self):
        """[New] 切换暂停/继续"""
        if not self.worker: return
        
        if self.worker.is_paused:
            # 当前暂停 -> 点击继续
            self.worker.set_pause(False)
            self.btn_start.setText("暂停测试")
            self.btn_start.setStyleSheet("background-color: #FF9500; color: white; border: none;")
            self.set_glow_state("run")
        else:
            # 当前运行 -> 点击暂停
            self.worker.set_pause(True)
            self.btn_start.setText("继续测试")
            self.btn_start.setStyleSheet("background-color: #34C759; color: white; border: none;")
            self.set_glow_state("pause")

    def update_start_btn_text(self, mode):
        """[New] 响应Worker的请求（如故障后变为继续）"""
        if mode == "continue":
            self.btn_start.setText("继续测试")
            self.btn_start.setStyleSheet("background-color: #34C759; color: white; border: none;")
            self.set_glow_state("error") # 故障时先红灯

    def open_manual(self):
        ManualControlDialog(self.in_dev.text(), self.combo_group.currentIndex() * 8, self, self).exec()

    def stop_test(self):
        if self.worker: self.worker.stop()

    def update_gui_data(self, val):
        self.lbl_pressure.setText(f"{val:.2f}")
        self.data_x.append(time.time() - self.start_time); self.data_y.append(val)
        if len(self.data_x) > 1000: self.data_x.pop(0); self.data_y.pop(0)
        self.curve.setData(self.data_x, self.data_y)

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
        self.lbl_timer.setText("--")
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
        self.settings_panel.setFixedHeight(60)
        sp_layout = QHBoxLayout(self.settings_panel); sp_layout.setContentsMargins(20, 0, 20, 0)
        
        self.btn_add = QPushButton(" + 增加台架 ")
        self.btn_add.setObjectName("BtnAdd")
        self.btn_add.setFixedSize(100, 36)
        self.btn_add.clicked.connect(self.add_station)
        
        self.btn_remove = QPushButton(" - 减少台架 ")
        self.btn_remove.setObjectName("BtnRemove")
        self.btn_remove.setFixedSize(100, 36)
        self.btn_remove.clicked.connect(self.remove_station)
        
        self.chk_sim = QCheckBox("仿真模式 (Simulation)")
        self.chk_sim.setStyleSheet("font-weight: bold; color: #007AFF;")
        self.chk_sim.stateChanged.connect(self.toggle_sim)
        
        self.lbl_dir = QLabel(os.getcwd())
        self.lbl_dir.setStyleSheet("color: #8E8E93;")
        
        btn_dir = QPushButton("更改路径")
        btn_dir.setObjectName("BtnSecondary")
        btn_dir.setFixedSize(100, 36)
        btn_dir.clicked.connect(self.set_dir)
        
        sp_layout.addWidget(self.btn_add); sp_layout.addWidget(self.btn_remove)
        line = QFrame(); line.setFrameShape(QFrame.Shape.VLine); line.setStyleSheet("color: #E5E5EA;")
        sp_layout.addWidget(line)
        sp_layout.addWidget(self.chk_sim); sp_layout.addStretch()
        sp_layout.addWidget(self.lbl_dir); sp_layout.addWidget(btn_dir)
        layout.addWidget(self.settings_panel)

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
        idx = len(self.stations) + 1
        st = StationWidget(idx, self.sig_log)
        self.stations.append(st)
        self.rearrange_layout()
        self.append_log(f"系统: 已增加台架 {idx}")

    def remove_station(self):
        if len(self.stations) <= 1:
            QMessageBox.warning(self, "操作无效", "至少需要保留一个台架。")
            return
        last_st = self.stations[-1]
        if last_st.worker and last_st.worker.isRunning():
             QMessageBox.critical(self, "禁止删除", f"台架 {last_st.idx} 正在运行中，请先停止测试后再删除。")
             return
        self.grid.removeWidget(last_st); last_st.deleteLater(); self.stations.pop()
        self.rearrange_layout()
        self.append_log(f"系统: 已移除台架 {last_st.idx}")

    def rearrange_layout(self):
        for i in reversed(range(self.grid.count())):
            w = self.grid.itemAt(i).widget()
            if w: w.setParent(None)
            
        count = len(self.stations)
        cols = 1 if count == 1 else (2 if count <= 4 else 3)
        
        for i in range(20): self.grid.setColumnStretch(i, 0); self.grid.setRowStretch(i, 0)
        for c in range(cols): self.grid.setColumnStretch(c, 1)
        for r in range((count + cols - 1) // cols): self.grid.setRowStretch(r, 1)

        for i, st in enumerate(self.stations):
            self.grid.addWidget(st, i // cols, i % cols)
            st.setVisible(True)

    def toggle_settings(self):
        self.settings_panel.setVisible(not self.settings_panel.isVisible())
        self.btn_toggle.setText("⚙️ 系统设置 (System Settings) " + ("▼" if self.settings_panel.isVisible() else "▶"))

    def toggle_sim(self, s):
        global SIMULATION_MODE
        SIMULATION_MODE = (s == 2)
        self.append_log(f"系统模式切换: {'仿真' if SIMULATION_MODE else '硬件'}")

    def set_dir(self):
        d = QFileDialog.getExistingDirectory()
        if d: self.lbl_dir.setText(d); os.chdir(d)

    def append_log(self, t):
        self.log.append(f"[{datetime.now().strftime('%H:%M:%S')}] {t}")
        self.log.verticalScrollBar().setValue(self.log.verticalScrollBar().maximum())

    def closeEvent(self, event):
        set_keep_awake(False)
        for s in self.stations:
            if s.worker and s.worker.isRunning(): s.stop_test()
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