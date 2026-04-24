# -*- coding: utf-8 -*-
"""
==============================================================================
项目名称 (Project)   : Compressor Lifetime Test System
文件名称 (Filename)  : compressor_lifetime_rev4.py
版本号   (Version)   : Rev 3.2
修改日期 (Date)      : 2025-12-11
版权声明 (Copyright) : Copyright (C) 2025 [Fresenius Medical Care China Develop Center]. All Rights Reserved.

功能描述 (Description):
    1. [修正]: Systemlog 增加了日期显示
    2. [UI]: 保持与 compressor_lifetime_3.py 一致的 IOS 风格 (圆角、阴影、呼吸灯)。
    3. [功能]: 
       - 高级配方编辑器 (支持多段泄压 release_seq)。
       - 动态参数布局 (QFormLayout 对齐)。
       - 手动模式实时压力显示。
==============================================================================
"""

import sys
import os
import time
import random
import csv
import ctypes
import copy
from datetime import datetime

from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QGridLayout, QLabel, 
                             QLineEdit, QPushButton, QCheckBox, QTextEdit, 
                             QFileDialog, QSplitter, QMessageBox,
                             QScrollArea, QDialog, QComboBox,
                             QSizePolicy, QFrame, QGraphicsDropShadowEffect,
                             QTableWidget, QTableWidgetItem, QHeaderView, 
                             QAbstractItemView, QGroupBox, QSpinBox, QDoubleSpinBox,
                             QListWidget, QListWidgetItem, QFormLayout)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QPropertyAnimation, QEasingCurve, QTimer
from PyQt6.QtGui import QFont, QColor, QPalette

import pyqtgraph as pg
import nidaqmx
from nidaqmx.constants import LineGrouping, TerminalConfiguration, AcquisitionType

# ============================================================================
# [SECTION 1] 全局配置与样式
# ============================================================================

IDX_MAP = {
    0: "V1 阀门", 1: "V2 阀门", 2: "V3 阀门", 3: "压缩机",
    4: "压力计供电", 5: "计数供电", 6: "计数信号", 7: "蜂鸣器/报警"
}

SIMULATION_MODE = False  

DEFAULT_RECIPE_TEMPLATE = [
    {
        "name": "阶段一: 标准保压",
        "type": "PRESSURIZE",
        "loops": 4,
        "params": {
            "timeout": 90.0,
            "do_action": [False, False, False, True,  True, True, False, False],
            "release_seq": [
                {"name": "大泄压 (V2+V3)", "time": 20.0, "do": [False, True, True, False, True, True, False, False]},
                {"name": "小泄压 (V1)", "time": 37.0, "do": [True, False, False, False, True, True, False, False]}
            ]
        }
    },
    {
        "name": "阶段二: 连续脉冲",
        "type": "PULSE",
        "loops": 14,
        "params": {
            "sub_loops": 10,
            "on_time": 1.0, "do_on":  [True, False, False, True, True, True, False, False],
            "off_time": 1.0, "do_off": [True, False, False, False, True, True, False, False],
            "release_seq": [
                {"name": "散热排气", "time": 20.0, "do": [True, True, True, False, True, True, False, False]}
            ]
        }
    }
]

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
    
    QFrame#SettingsPanel { background-color: #FFFFFF; border-bottom: 1px solid #E5E5EA; }
    QFrame#Card { background-color: #FFFFFF; border-radius: 16px; border: 1px solid #E5E5EA; }
    
    QLabel#CardTitle { font-size: 18px; font-weight: bold; color: #000000; background-color: transparent; }
    QLabel { background-color: transparent; color: #1C1C1E; }
    QLabel[class="SubLabel"] { font-size: 12px; color: #8E8E93; }

    QLineEdit, QComboBox, QSpinBox, QDoubleSpinBox {
        background-color: #F2F2F7; border: 1px solid #E5E5EA; border-radius: 8px;
        padding: 6px 10px; color: #000000;
    }
    QLineEdit:focus, QComboBox:focus, QSpinBox:focus { border: 1px solid #007AFF; background-color: #FFFFFF; }
    QComboBox::drop-down { border: none; }

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

    QScrollArea { border: none; background-color: transparent; }
    QWidget#ScrollContents { background-color: transparent; }
    QSplitter::handle { background-color: #E5E5EA; margin: 1px; }
    QSplitter::handle:hover { background-color: #007AFF; }
    QTextEdit {
        background-color: #F9F9F9; color: #333333; border-radius: 8px;
        font-family: "Menlo", "Consolas", monospace; border: 1px solid #E5E5EA;
    }
    QDialog { background-color: #FFFFFF; }
    QTableWidget { gridline-color: #E5E5EA; border: 1px solid #E5E5EA; border-radius: 8px; }
    QHeaderView::section { background-color: #F2F2F7; border: none; padding: 4px; font-weight: bold; }
    QGroupBox { font-weight: bold; border: 1px solid #E5E5EA; border-radius: 8px; margin-top: 20px; }
    QGroupBox::title { subcontrol-origin: margin; left: 10px; padding: 0 3px; color: #8E8E93; }
"""

def set_keep_awake(enable=True):
    try:
        if enable: ctypes.windll.kernel32.SetThreadExecutionState(0x80000003)
        else: ctypes.windll.kernel32.SetThreadExecutionState(0x80000000)
    except: pass

class RetryCycleError(Exception): pass


# ============================================================================
# [SECTION 2] Worker Logic
# ============================================================================

class TestWorker(QThread):
    sig_log = pyqtSignal(str); sig_pressure = pyqtSignal(float); sig_status = pyqtSignal(str, str)
    sig_progress = pyqtSignal(int); sig_finished = pyqtSignal(); sig_error = pyqtSignal(str)
    sig_timer = pyqtSignal(str); sig_button_update = pyqtSignal(str)

    def __init__(self, config, group_offset, log_dir, recipe):
        super().__init__()
        self.config = config; self.offset = group_offset; self.log_dir = log_dir; self.recipe = recipe
        self.is_running = True; self.is_paused = False; self.do_task = None; self.ai_task = None
        self.dev_name = config['device']; self.target_cycles = int(config['cycles'])
        self.target_p = float(config['target_p']); self.floor_p = float(config['floor_p'])
        self.max_p = float(config['max_p']); self.sim_mode = config['simulation']
        self._sim_p_val = 0.0; self._last_pressure = 0.0; self.step_max_p = 0.0; self.step_min_p = 99.9
        self.fault_triggered = False; self.last_do_states = [False] * 8

    def run(self):
        try:
            self.setup_hardware(); self.create_log_file()
            self.sig_log.emit(f"启动: {self.dev_name} [Line {self.offset}-{self.offset+7}]")
            curr_cycle = 1
            while curr_cycle <= self.target_cycles:
                if not self.is_running: break
                try:
                    self.check_pause_state()
                    self.sig_status.emit(f"Cycle {curr_cycle}: Start", STATUS_STYLES["run"])
                    for step in self.recipe:
                        if not self.is_running: break
                        name, typ, loops = step.get("name",""), step.get("type","PRESSURIZE"), int(step.get("loops",1))
                        self.sig_log.emit(f"Cycle {curr_cycle}: {name} ({loops}x)")
                        if typ == "PRESSURIZE": 
                            if not self.run_pressurize(curr_cycle, loops, name, step.get("params",{})): break
                        elif typ == "PULSE": 
                            if not self.run_pulse(curr_cycle, loops, name, step.get("params",{})): break
                    if not self.is_running: break
                    self.sig_status.emit(f"Cycle {curr_cycle}: Count", STATUS_STYLES["run"]); self._trigger_counter()
                    self.sleep_smart(1.0); self.sig_progress.emit(curr_cycle); curr_cycle += 1
                except RetryCycleError:
                    if not self.is_running: break
                    self.sig_log.emit(f"Cycle {curr_cycle} 复位重试..."); self.finalize_success(); time.sleep(2.0); continue
            if self.is_running: self.finalize_success(); self.sig_status.emit("测试完成", STATUS_STYLES["run"])
            else: self.sig_status.emit("已停止", STATUS_STYLES["err"])
        except Exception as e: self.sig_error.emit(f"Error: {e}"); self.emergency_shutdown()
        finally: self.cleanup(); self.sig_finished.emit()

    def run_pressurize(self, cycle, loops, name, params):
        to = params.get("timeout", 90.0); do_act = params.get("do_action", [False]*8)
        rel_seq = params.get("release_seq", [])
        loop_rel_do = rel_seq[0]["do"] if rel_seq else [True]*8 
        success = 0
        for i in range(loops):
            if not self.is_running: return False
            self.check_pause_state(); self.step_max_p=0; self.step_min_p=99.9
            self.sig_status.emit(f"{name} ({i+1}/{loops}): 加压", STATUS_STYLES["run"])
            t0 = time.time(); reached = False; releasing = False
            while time.time()-t0 < to:
                if not self.is_running: return False
                if self.is_paused: self.check_pause_state()
                self.sig_timer.emit(f"{to-(time.time()-t0):.1f}"); p = self.read_pressure()
                if not releasing:
                    self.write_do(do_act)
                    if p >= self.target_p: reached = True; releasing = True; self.sig_status.emit(f"{name}: 回落", STATUS_STYLES["run"])
                else:
                    self.write_do(loop_rel_do)
                    if p <= self.floor_p: releasing = False; self.sig_status.emit(f"{name}: 再加压", STATUS_STYLES["run"])
                time.sleep(0.1)
            if reached: success += 1
            else: self.sig_log.emit(f"{name} loop {i+1} 未达标")
            if not self.run_release_seq(name, rel_seq): return False
            self.log_csv(cycle, "PRESS", f"{i+1}/{loops}", self.read_pressure(True))
        if success == 0: self.trigger_fault(f"{name}: 无法建立压力"); return False
        return True

    def run_pulse(self, cycle, loops, name, params):
        subs = params.get("sub_loops", 10)
        t_on = params.get("on_time", 1.0); d_on = params.get("do_on", [False]*8)
        t_off = params.get("off_time", 1.0); d_off = params.get("do_off", [False]*8)
        for i in range(loops):
            if not self.is_running: return False
            self.check_pause_state(); self.step_max_p=0; self.step_min_p=99.9
            for j in range(subs):
                if not self.is_running: return False
                self.sig_status.emit(f"{name}: Pulse {j+1}/{subs}", STATUS_STYLES["run"])
                self.write_do(d_on); 
                if not self.sleep_smart(t_on): return False
                self.write_do(d_off); 
                if not self.sleep_smart(t_off): return False
            if not self.run_release_seq(name, params.get("release_seq", [])): return False
            self.log_csv(cycle, "PULSE", f"{i+1}/{loops}", self.read_pressure(True))
        return True

    def run_release_seq(self, prefix, seq):
        for idx, s in enumerate(seq):
            if not self.is_running: return False
            self.sig_status.emit(f"{prefix}: {s.get('name', f'Rel {idx+1}')}", STATUS_STYLES["run"])
            self.write_do(s.get("do", [True]*8))
            if not self.sleep_smart(s.get("time", 10.0)): return False
        return True

    def check_pause_state(self):
        if self.is_paused and self.is_running:
            self.sig_status.emit("暂停中", STATUS_STYLES["pause"])
            safe = list(self.last_do_states); safe[3] = False 
            if self.fault_triggered: safe[7] = True
            try: self.do_task.write(safe)
            except: pass
            while self.is_paused and self.is_running: time.sleep(0.1); self.read_pressure(True)
            if self.is_running:
                if self.fault_triggered: self.fault_triggered = False; raise RetryCycleError()
                else: self.write_do(self.last_do_states)
    
    def trigger_fault(self, m): self.fault_triggered=True; self.is_paused=True; self.sig_error.emit(m); self.sig_button_update.emit("c"); self.check_pause_state()
    def sleep_smart(self, d):
        t=time.time()
        while time.time()-t < d:
            if not self.is_running: return False
            if self.is_paused: self.check_pause_state()
            self.sig_timer.emit(f"{d-(time.time()-t):.1f}"); self.read_pressure(); time.sleep(0.1)
        self.sig_timer.emit("0.0"); return True
    def setup_hardware(self):
        if self.sim_mode: return
        self.do_task = nidaqmx.Task(); self.do_task.do_channels.add_do_chan(f"{self.dev_name}/port0/line{self.offset}:{self.offset+7}", line_grouping=LineGrouping.CHAN_PER_LINE); self.do_task.start()
        self.ai_task = nidaqmx.Task(); self.ai_task.ai_channels.add_ai_voltage_chan(f"{self.dev_name}/ai{self.offset//8}", terminal_config=TerminalConfiguration.RSE, min_val=-10, max_val=10)
        self.ai_task.timing.cfg_samp_clk_timing(rate=500, sample_mode=AcquisitionType.CONTINUOUS); self.ai_task.start()
    def read_pressure(self, silent=False):
        if self.sim_mode: return self._sim_p(silent)
        try:
            d = self.ai_task.read(number_of_samples_per_channel=nidaqmx.constants.READ_ALL_AVAILABLE)
            if not d: return self._last_pressure
            v = max(0, (sum(d)/len(d)-1)*2.5); 
            v = 0.8*v + 0.2*self._last_pressure; 
            self._last_pressure = v
            if not silent: self.sig_pressure.emit(v)
            if v>self.step_max_p: self.step_max_p=v
            if v<self.step_min_p: self.step_min_p=v
            if v>self.max_p: self.trigger_fault(f"OverP: {v:.2f}")
            return v
        except: return 0.0
    def write_do(self, s):
        if not self.is_running: return
        self.last_do_states = list(s)
        if self.sim_mode: self._sim_r(s); return
        try: self.do_task.write(s)
        except Exception as e: self.sig_error.emit(str(e))
    def _trigger_counter(self): s=[False]*8; s[1]=s[2]=s[4]=s[5]=s[6]=True; self.write_do(s)
    def finalize_success(self): 
        if not self.sim_mode and self.do_task: s=[False]*8; s[4]=s[5]=True; self.do_task.write(s)
    def cleanup(self):
        if self.do_task: 
            try: self.do_task.write([False]*8); self.do_task.close()
            except: pass
        if self.ai_task: 
            try: self.ai_task.close()
            except: pass
    def create_log_file(self):
        ts = datetime.now().strftime("%Y%m%d_%H%M%S"); self.csv_file = os.path.join(self.log_dir, f"Log_{self.dev_name}_Grp{self.offset//8}_{ts}.csv")
        with open(self.csv_file, 'w', newline='') as f: csv.writer(f).writerow(["Date","Time","Cycle","Type","Step","EndP","MaxP","MinP"])
    def log_csv(self, c, t, s, p):
        if not self.csv_file: return
        with open(self.csv_file, 'a', newline='') as f: n=datetime.now(); csv.writer(f).writerow([n.strftime("%Y-%m-%d"), n.strftime("%H:%M:%S"), c, t, s, f"{p:.2f}", f"{self.step_max_p:.2f}", f"{self.step_min_p:.2f}"])
    def emergency_shutdown(self): 
        if self.do_task: 
            try: self.do_task.stop(); self.do_task.start(); self.do_task.write([False]*8)
            except: pass
    def stop(self): self.is_running = False; self.is_paused = False; self.emergency_shutdown()
    def set_pause(self, p): self.is_paused = p
    def _sim_p(self, s): self._sim_p_val = max(0, self._sim_p_val+random.uniform(-0.05, 0.05)); self.sig_pressure.emit(self._sim_p_val) if not s else None; return self._sim_p_val
    def _sim_r(self, s): self._sim_p_val += 0.2 if s[3] and s[0] else (-0.3 if s[1] or s[2] else 0)

# ============================================================================
# [SECTION 3] UI Components (Fixed Syntax)
# ============================================================================

class DOSelector(QWidget):
    def __init__(self, title, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self); layout.setContentsMargins(0,2,0,2)
        gb = QGroupBox(title)
        grid = QGridLayout(gb); grid.setSpacing(8)
        self.boxes = []
        for i in range(8):
            chk = QCheckBox(IDX_MAP.get(i, f"IO {i}"))
            self.boxes.append(chk); grid.addWidget(chk, i//4, i%4)
        layout.addWidget(gb)
    def get(self): return [b.isChecked() for b in self.boxes]
    def set(self, s): 
        for i, v in enumerate(s): 
            if i<len(self.boxes): self.boxes[i].setChecked(bool(v))
    def connect_change(self, func):
        for b in self.boxes: b.clicked.connect(func)

class ReleaseSeqEditor(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.data = []; self.cb = None
        lay = QVBoxLayout(self); lay.setContentsMargins(0,0,0,0)
        
        self.table = QTableWidget(0, 3); self.table.setHorizontalHeaderLabels(["阶段名", "时长(s)", "DO"])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.itemClicked.connect(self.on_click); self.table.setMinimumHeight(120)
        lay.addWidget(self.table)
        
        btn_lay = QHBoxLayout()
        b_add = QPushButton("添加"); b_add.clicked.connect(self.add); b_add.setFixedWidth(80)
        b_del = QPushButton("删除"); b_del.clicked.connect(self.rem); b_del.setFixedWidth(80)
        btn_lay.addWidget(b_add); btn_lay.addWidget(b_del); btn_lay.addStretch()
        lay.addLayout(btn_lay)
        
        self.grp = QGroupBox("阶段详情配置"); self.grp.setEnabled(False)
        gl = QFormLayout(self.grp); gl.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.ExpandingFieldsGrow)
        self.n_in = QLineEdit()
        self.t_in = QDoubleSpinBox(); self.t_in.setRange(0.1, 9999)
        self.do_sel = DOSelector("DO 状态")
        
        gl.addRow("名称:", self.n_in); gl.addRow("时长(s):", self.t_in); gl.addRow(self.do_sel)
        lay.addWidget(self.grp)
        
        self.n_in.textChanged.connect(self.sync)
        self.t_in.valueChanged.connect(self.sync)
        self.do_sel.connect_change(self.sync)

    def set_data(self, d): self.data = copy.deepcopy(d) if d else []; self.refresh(); self.grp.setEnabled(False)
    def get_data(self): return self.data
    def refresh(self):
        r = self.table.currentRow(); self.table.setRowCount(0)
        for i, d in enumerate(self.data):
            self.table.insertRow(i)
            self.table.setItem(i, 0, QTableWidgetItem(d.get("name","")))
            self.table.setItem(i, 1, QTableWidgetItem(str(d.get("time",0))))
            do_s = ",".join([str(k) for k,v in enumerate(d.get("do",[])) if v])
            self.table.setItem(i, 2, QTableWidgetItem(do_s if do_s else "Off"))
        if r>=0 and r<self.table.rowCount(): self.table.selectRow(r)
    def on_click(self):
        r = self.table.currentRow()
        if r<0: return
        self.grp.setEnabled(True); d = self.data[r]
        self.blockSignals(True)
        self.n_in.setText(d.get("name","")); self.t_in.setValue(d.get("time",10.0)); self.do_sel.set(d.get("do",[True]*8))
        self.blockSignals(False)
    def sync(self):
        r = self.table.currentRow()
        if r<0 or self.signalsBlocked(): return
        self.data[r]["name"] = self.n_in.text()
        self.data[r]["time"] = self.t_in.value()
        self.data[r]["do"] = self.do_sel.get()
        self.table.item(r,0).setText(self.data[r]["name"]); self.table.item(r,1).setText(str(self.data[r]["time"]))
        do_s = ",".join([str(k) for k,v in enumerate(self.data[r]["do"]) if v])
        self.table.item(r,2).setText(do_s if do_s else "Off")
        if self.cb: self.cb()
    def add(self): self.data.append({"name":"新阶段","time":10,"do":[True]*8}); self.refresh(); self.table.selectRow(len(self.data)-1); self.on_click(); self.sync()
    def rem(self): 
        r=self.table.currentRow()
        if r>=0: self.data.pop(r); self.refresh(); self.grp.setEnabled(False); self.sync()

class RecipeEditorDialog(QDialog):
    def __init__(self, current_recipe, parent=None):
        super().__init__(parent)
        self.setWindowTitle("高级配方配置 (Advanced Recipe Config)")
        self.resize(1100, 700)
        self.recipe = copy.deepcopy(current_recipe)
        self.curr_step = {}
        self.init_ui()

    def init_ui(self):
        splitter = QSplitter(Qt.Orientation.Horizontal)
        main_layout = QVBoxLayout(self)
        
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget); left_layout.setContentsMargins(0,0,10,0)
        left_layout.addWidget(QLabel("步骤列表 (Steps)"))
        self.list_w = QListWidget()
        self.list_w.currentRowChanged.connect(self.load_step)
        left_layout.addWidget(self.list_w)
        
        btn_grid = QGridLayout()
        b_add = QPushButton("添加"); b_add.clicked.connect(self.add_step)
        b_del = QPushButton("删除"); b_del.clicked.connect(self.del_step)
        b_dup = QPushButton("复制"); b_dup.clicked.connect(self.dup_step)
        b_up = QPushButton("▲"); b_up.clicked.connect(lambda: self.move_step(-1))
        b_dn = QPushButton("▼"); b_dn.clicked.connect(lambda: self.move_step(1))
        btn_grid.addWidget(b_add,0,0); btn_grid.addWidget(b_del,0,1)
        btn_grid.addWidget(b_dup,1,0); btn_grid.addWidget(b_up,1,1); btn_grid.addWidget(b_dn,1,2)
        left_layout.addLayout(btn_grid)
        
        left_widget.setLayout(left_layout)
        splitter.addWidget(left_widget)
        
        scroll = QScrollArea(); scroll.setWidgetResizable(True)
        right_widget = QWidget(); self.p_layout = QVBoxLayout(right_widget)
        
        gb_info = QGroupBox("基础信息 (Basic Info)"); form_info = QFormLayout(gb_info)
        self.in_name = QLineEdit()
        self.in_loops = QSpinBox(); self.in_loops.setRange(1, 9999)
        self.cb_type = QComboBox(); self.cb_type.addItems(["PRESSURIZE", "PULSE"])
        self.cb_type.currentTextChanged.connect(self.refresh_dynamic_ui)
        
        form_info.addRow("步骤名称:", self.in_name)
        form_info.addRow("循环次数:", self.in_loops)
        form_info.addRow("动作类型:", self.cb_type)
        self.p_layout.addWidget(gb_info)
        
        self.gb_dyn = QGroupBox("动作参数 (Action Params)"); self.dyn_layout = QVBoxLayout(self.gb_dyn)
        self.p_layout.addWidget(self.gb_dyn)
        
        self.rel_editor = ReleaseSeqEditor()
        self.rel_editor.cb = self.save_rel
        self.gb_rel = QGroupBox("泄压序列 (Release Sequence)")
        l_rel = QVBoxLayout(self.gb_rel); l_rel.addWidget(self.rel_editor)
        self.p_layout.addWidget(self.gb_rel)
        
        self.p_layout.addStretch()
        scroll.setWidget(right_widget)
        splitter.addWidget(scroll); splitter.setSizes([300, 700])
        main_layout.addWidget(splitter)
        
        b_box = QHBoxLayout()
        b_save = QPushButton("保存并应用"); b_save.setObjectName("BtnPrimary"); b_save.clicked.connect(self.accept)
        b_cancel = QPushButton("取消"); b_cancel.clicked.connect(self.reject)
        b_box.addStretch(); b_box.addWidget(b_cancel); b_box.addWidget(b_save)
        main_layout.addLayout(b_box)
        
        self.in_name.textChanged.connect(self.save_meta)
        self.in_loops.valueChanged.connect(self.save_meta)
        self.cb_type.currentTextChanged.connect(self.save_meta)
        
        self.refresh_list(); 
        if self.recipe: self.list_w.setCurrentRow(0)

    def refresh_list(self):
        r = self.list_w.currentRow(); self.list_w.clear()
        for i, s in enumerate(self.recipe):
            self.list_w.addItem(f"{i+1}. {s.get('name')} ({s.get('type')}) x{s.get('loops')}")
        if r >= 0 and r < self.list_w.count(): self.list_w.setCurrentRow(r)

    def load_step(self, r):
        if r < 0 or r >= len(self.recipe): return
        self.curr_step = self.recipe[r]
        self.block_sig(True)
        self.in_name.setText(self.curr_step.get("name",""))
        self.in_loops.setValue(self.curr_step.get("loops",1))
        self.cb_type.setCurrentText(self.curr_step.get("type","PRESSURIZE"))
        self.block_sig(False)
        self.rel_editor.set_data(self.curr_step.get("params",{}).get("release_seq",[]))
        self.refresh_dynamic_ui()

    def refresh_dynamic_ui(self):
        while self.dyn_layout.count(): 
            w = self.dyn_layout.takeAt(0).widget(); 
            if w: w.deleteLater()
        t = self.cb_type.currentText(); p = self.curr_step.get("params", {})
        if t == "PRESSURIZE":
            self.add_p_dbl("timeout", "超时时间 (s)", p.get("timeout", 90))
            self.add_p_do("do_action", "加压动作 DO", p.get("do_action", [False]*8))
        elif t == "PULSE":
            self.add_p_int("sub_loops", "内部脉冲数", p.get("sub_loops", 10))
            self.add_p_dbl("on_time", "开阀时间 (s)", p.get("on_time", 1.0))
            self.add_p_do("do_on", "脉冲 ON DO", p.get("do_on", [False]*8))
            self.add_p_dbl("off_time", "关阀时间 (s)", p.get("off_time", 1.0))
            self.add_p_do("do_off", "脉冲 OFF DO", p.get("do_off", [False]*8))

    def save_meta(self):
        if not self.curr_step: return
        self.curr_step["name"] = self.in_name.text()
        self.curr_step["loops"] = self.in_loops.value()
        self.curr_step["type"] = self.cb_type.currentText()
        r = self.list_w.currentRow()
        if r>=0: self.list_w.item(r).setText(f"{r+1}. {self.curr_step['name']} ({self.curr_step['type']}) x{self.curr_step['loops']}")
        if self.sender() == self.cb_type: self.refresh_dynamic_ui()

    def save_p(self, k, v): 
        if "params" not in self.curr_step: self.curr_step["params"]={}
        self.curr_step["params"][k] = v
    def save_rel(self):
        if "params" not in self.curr_step: self.curr_step["params"]={}
        self.curr_step["params"]["release_seq"] = self.rel_editor.get_data()

    def add_p_dbl(self, k, l, v):
        h = QHBoxLayout(); s = QDoubleSpinBox(); s.setRange(0,9999); s.setValue(v)
        s.valueChanged.connect(lambda x: self.save_p(k,x))
        h.addWidget(QLabel(l)); h.addWidget(s); self.dyn_layout.addLayout(h)
    def add_p_int(self, k, l, v):
        h = QHBoxLayout(); s = QSpinBox(); s.setRange(0,9999); s.setValue(v)
        s.valueChanged.connect(lambda x: self.save_p(k,x))
        h.addWidget(QLabel(l)); h.addWidget(s); self.dyn_layout.addLayout(h)
    def add_p_do(self, k, l, v):
        w = DOSelector(l); w.set(v); w.connect_change(lambda: self.save_p(k, w.get()))
        self.dyn_layout.addWidget(w)
    
    def block_sig(self, b): self.in_name.blockSignals(b); self.in_loops.blockSignals(b); self.cb_type.blockSignals(b)
    def add_step(self): self.recipe.append({"name":"新步骤","type":"PRESSURIZE","loops":1,"params":{}}); self.refresh_list(); self.list_w.setCurrentRow(len(self.recipe)-1)
    def del_step(self): 
        r=self.list_w.currentRow()
        if r>=0: self.recipe.pop(r); self.refresh_list()
    def dup_step(self):
        r=self.list_w.currentRow()
        if r>=0: self.recipe.insert(r+1, copy.deepcopy(self.recipe[r])); self.refresh_list(); self.list_w.setCurrentRow(r+1)
    def move_step(self, d):
        r=self.list_w.currentRow(); nr=r+d
        if 0<=nr<len(self.recipe): self.recipe[r],self.recipe[nr]=self.recipe[nr],self.recipe[r]; self.refresh_list(); self.list_w.setCurrentRow(nr)

class ManualControlDialog(QDialog):
    def __init__(self, dev, off, st, parent=None):
        super().__init__(parent); self.setWindowTitle(f"调试 - {dev}"); self.setFixedSize(460,580)
        self.dev=dev; self.off=off; self.st=st; self.do=None; self.ai=None; self.sts=[False]*8; self.btns=[]
        self.init(); self.start(); self.tmr=QTimer(self); self.tmr.timeout.connect(self.upd); self.tmr.start(200)
    def init(self):
        l=QVBoxLayout(self); l.setSpacing(15); l.setContentsMargins(20,20,20,20)
        l.addWidget(QLabel(f"Line {self.off}-{self.off+7}", alignment=Qt.AlignmentFlag.AlignCenter, styleSheet="font-size:18px; font-weight:bold;"))
        pf=QFrame(); pf.setStyleSheet("background:#F2F2F7; border-radius:8px; border:1px solid #E5E5EA;")
        pl=QHBoxLayout(pf); self.p_lbl=QLabel("0.00 Bar", styleSheet="font-size:24px; font-weight:bold; color:#007AFF;")
        pl.addWidget(QLabel("当前压力:")); pl.addStretch(); pl.addWidget(self.p_lbl); l.addWidget(pf)
        g=QGridLayout(); g.setSpacing(10)
        for i in range(8):
            b=QPushButton(f"{IDX_MAP.get(i)}\nOFF"); b.setCheckable(True); b.setFixedHeight(60); b.clicked.connect(lambda _,x=i:self.tg(x))
            b.setStyleSheet("background:#F2F2F7; color:#8E8E93; border:1px solid #E5E5EA;"); g.addWidget(b,i//2,i%2); self.btns.append(b)
        l.addLayout(g)
        b_c=QPushButton("关闭", objectName="BtnPrimary"); b_c.clicked.connect(self.accept); l.addWidget(b_c)
    def start(self):
        if SIMULATION_MODE: return
        try:
            self.do=nidaqmx.Task(); self.do.do_channels.add_do_chan(f"{self.dev}/port0/line{self.off}:{self.off+7}"); self.do.start(); self.do.write([False]*8)
            self.ai=nidaqmx.Task(); self.ai.ai_channels.add_ai_voltage_chan(f"{self.dev}/ai{self.off//8}", terminal_config=TerminalConfiguration.RSE, min_val=-10, max_val=10)
            self.ai.start()
        except Exception as e: QMessageBox.warning(self,"Err",str(e))
    def upd(self):
        if SIMULATION_MODE: self.p_lbl.setText(f"{random.uniform(0,0.1):.2f} Bar"); return
        if self.ai: 
            try: self.p_lbl.setText(f"{max(0,(self.ai.read()-1)*2.5):.2f} Bar")
            except: pass
    def tg(self, i):
        self.sts[i]=self.btns[i].isChecked()
        self.btns[i].setText(f"{IDX_MAP.get(i)}\n{'ON' if self.sts[i] else 'OFF'}")
        self.btns[i].setStyleSheet(f"background:{'#34C759' if self.sts[i] else '#F2F2F7'}; color:{'white' if self.sts[i] else '#8E8E93'}; border:none;" if self.sts[i] else "background:#F2F2F7; color:#8E8E93; border:1px solid #E5E5EA;")
        if self.do: self.do.write(self.sts)
    def closeEvent(self, e): self.tmr.stop(); self.do.close() if self.do else None; self.ai.close() if self.ai else None; e.accept()

class StationWidget(QFrame):
    def __init__(self, idx, log):
        super().__init__(); self.idx=idx; self.log=log; self.recipe=copy.deepcopy(DEFAULT_RECIPE_TEMPLATE)
        self.worker=None; self.hw=False; self.init(); self.anim()
    def anim(self):
        self.eff=QGraphicsDropShadowEffect(self); self.eff.setBlurRadius(40); self.eff.setColor(QColor(0,0,0,25)); self.eff.setYOffset(4)
        self.setGraphicsEffect(self.eff)
        self.an=QPropertyAnimation(self.eff, b"color"); self.an.setDuration(1500); self.an.setLoopCount(-1); self.an.setEasingCurve(QEasingCurve.Type.InOutSine)
    def set_st(self, s):
        self.an.stop(); c={"run":"#34C759","err":"#FF3B30","pause":"#FF9500"}.get(s)
        if c: self.an.setStartValue(QColor(c)); self.an.setEndValue(QColor(c)); self.an.start()
        else: self.eff.setColor(QColor(0,0,0,25))
    def init(self):
        self.setObjectName("Card"); self.setMinimumHeight(480)
        l=QVBoxLayout(self); l.setSpacing(12); l.setContentsMargins(24,24,24,24)
        
        h=QHBoxLayout(); self.l_t=QLabel(f"Station {self.idx}"); self.l_t.setObjectName("CardTitle"); self.l_s=QLabel("待机"); self.l_s.setStyleSheet(STATUS_STYLES["stop"])
        h.addWidget(self.l_t); h.addStretch(); h.addWidget(self.l_s); l.addLayout(h)
        
        c=QHBoxLayout(); self.dev=QLineEdit("Dev1"); self.dev.setFixedWidth(70); self.grp=QComboBox(); self.grp.addItems([f"Grp {i}" for i in range(4)]); self.grp.setCurrentIndex((self.idx-1)%4)
        self.b_cn=QPushButton("连接"); self.b_cn.setObjectName("BtnSecondary"); self.b_cn.setCheckable(True); self.b_cn.setFixedWidth(70); self.b_cn.clicked.connect(self.conn)
        self.b_rec=QPushButton("配方设置"); self.b_rec.setObjectName("BtnSecondary"); self.b_rec.clicked.connect(self.rec)
        c.addWidget(QLabel("设备:")); c.addWidget(self.dev); c.addWidget(self.grp); c.addWidget(self.b_cn); c.addWidget(self.b_rec); l.addLayout(c)
        
        p=QGridLayout(); p.setSpacing(10)
        self.cyc=QLineEdit("350"); self.tar=QLineEdit("2.02"); self.flr=QLineEdit("0.02"); self.mx=QLineEdit("2.5"); self.mx.setStyleSheet("color:#FF3B30; font-weight:bold;")
        p.addWidget(QLabel("目标循环:"),0,0); p.addWidget(self.cyc,0,1); p.addWidget(QLabel("高压 (Bar):"),0,2); p.addWidget(self.tar,0,3)
        p.addWidget(QLabel("低压 (Bar):"),1,0); p.addWidget(self.flr,1,1); p.addWidget(QLabel("保护上限:"),1,2); p.addWidget(self.mx,1,3); l.addLayout(p)
        
        self.plt=pg.PlotWidget(background="w"); self.plt.setMinimumHeight(160); self.plt.showGrid(x=True,y=True,alpha=0.15); self.crv=self.plt.plot(pen=pg.mkPen("#007AFF", width=2)); l.addWidget(self.plt)
        
        i=QHBoxLayout(); v1=QVBoxLayout(); self.tm=QLabel("--"); self.tm.setStyleSheet("font-size:22px; font-weight:bold; color:#FF9500")
        l1=QLabel("倒计时 (s)"); l1.setProperty("class", "SubLabel"); v1.addWidget(l1); v1.addWidget(self.tm)
        v2=QVBoxLayout(); v2.setAlignment(Qt.AlignmentFlag.AlignCenter); self.pg=QLabel("0 / 350"); self.pg.setStyleSheet("font-size:22px; font-weight:bold;")
        l2=QLabel("循环进度"); l2.setProperty("class", "SubLabel"); v2.addWidget(l2); v2.addWidget(self.pg)
        v3=QVBoxLayout(); v3.setAlignment(Qt.AlignmentFlag.AlignRight); self.ps=QLabel("0.00"); self.ps.setStyleSheet("font-size:28px; font-weight:bold; color:#007AFF;")
        l3=QLabel("压力 (Bar)"); l3.setProperty("class", "SubLabel"); l3.setAlignment(Qt.AlignmentFlag.AlignRight); v3.addWidget(l3); v3.addWidget(self.ps)
        i.addLayout(v1); i.addStretch(); i.addLayout(v2); i.addStretch(); i.addLayout(v3); l.addLayout(i); l.addStretch()
        
        b=QHBoxLayout(); self.b_mn=QPushButton("调试"); self.b_mn.setObjectName("BtnSecondary"); self.b_mn.clicked.connect(self.man)
        self.b_st=QPushButton("开始测试"); self.b_st.setObjectName("BtnPrimary"); self.b_st.setEnabled(False); self.b_st.clicked.connect(self.run)
        self.b_sp=QPushButton("紧急停止"); self.b_sp.setObjectName("BtnDanger"); self.b_sp.setEnabled(False); self.b_sp.clicked.connect(self.stp)
        b.addWidget(self.b_mn); b.addWidget(self.b_st, 2); b.addWidget(self.b_sp); l.addLayout(b)

    def conn(self):
        if self.b_cn.isChecked():
            if not SIMULATION_MODE:
                try: 
                    t=nidaqmx.Task(); t.do_channels.add_do_chan(f"{self.dev.text()}/port0/line{self.grp.currentIndex()*8}"); t.close()
                except Exception as e: QMessageBox.warning(self,"Err",str(e)); self.b_cn.setChecked(False); return
            self.hw=True; self.dev.setEnabled(False); self.grp.setEnabled(False); self.b_cn.setText("已连接"); self.b_cn.setObjectName("BtnSuccess"); self.b_st.setEnabled(True); self.b_cn.setStyleSheet("")
        else: self.hw=False; self.dev.setEnabled(True); self.grp.setEnabled(True); self.b_cn.setText("连接"); self.b_cn.setObjectName("BtnSecondary"); self.b_st.setEnabled(False); self.b_cn.setStyleSheet("")
    def run(self):
        if self.worker and self.worker.isRunning():
            self.worker.set_pause(not self.worker.is_paused)
            if self.worker.is_paused: self.b_st.setText("继续测试"); self.b_st.setStyleSheet("background:#34C759; color:white; border:none;"); self.set_st("pause")
            else: self.b_st.setText("暂停测试"); self.b_st.setStyleSheet("background:#FF9500; color:white; border:none;"); self.set_st("run")
            return
        cfg={'device':self.dev.text(),'cycles':self.cyc.text(),'target_p':self.tar.text(),'floor_p':self.flr.text(),'max_p':self.mx.text(),'simulation':SIMULATION_MODE}
        self.dx=[]; self.dy=[]; self.t0=time.time(); self.pg.setText(f"0 / {cfg['cycles']}")
        self.worker=TestWorker(cfg, self.grp.currentIndex()*8, os.getcwd(), self.recipe)
        self.worker.sig_pressure.connect(self.upd); self.worker.sig_timer.connect(self.tm.setText)
        self.worker.sig_status.connect(lambda m,s: (self.l_s.setText(m), self.l_s.setStyleSheet(s)))
        self.worker.sig_progress.connect(lambda c: self.pg.setText(f"{c} / {self.cyc.text()}"))
        self.worker.sig_log.connect(lambda m: self.log.emit(f"[S{self.idx}] {m}"))
        self.worker.sig_finished.connect(self.fin); self.worker.sig_error.connect(self.err)
        self.worker.sig_button_update.connect(lambda _: (self.b_st.setText("继续测试"), self.set_st("err")))
        self.b_st.setText("暂停测试"); self.b_st.setStyleSheet("background:#FF9500; color:white; border:none;"); self.b_mn.setEnabled(False); self.b_cn.setEnabled(False); self.b_sp.setEnabled(True); self.b_rec.setEnabled(False); self.set_st("run"); self.worker.start()
    def stp(self): self.worker.stop() if self.worker else None
    def man(self): ManualControlDialog(self.dev.text(), self.grp.currentIndex()*8, self, self).exec()
    def rec(self): 
        d=RecipeEditorDialog(self.recipe, self)
        if d.exec(): self.recipe=d.recipe; self.log.emit(f"S{self.idx} 配方更新")
    def upd(self, v): 
        self.ps.setText(f"{v:.2f}"); self.dx.append(time.time()-self.t0); self.dy.append(v)
        if len(self.dx)>1000: self.dx.pop(0); self.dy.pop(0)
        self.crv.setData(self.dx, self.dy)
    def err(self, m): self.set_st("err"); self.log.emit(f"[S{self.idx} ERR] {m}")
    def fin(self): 
        self.b_st.setText("开始测试"); self.b_st.setObjectName("BtnPrimary"); self.b_st.setStyleSheet(""); self.b_st.setEnabled(True)
        self.b_mn.setEnabled(True); self.b_cn.setEnabled(True); self.b_sp.setEnabled(False); self.b_rec.setEnabled(True); self.set_st("idle")

class MainWindow(QMainWindow):
    sig_log = pyqtSignal(str)
    def __init__(self):
        super().__init__(); self.setWindowTitle("Compressor Lifetime Rev 8.1"); self.resize(1440,960)
        w=QWidget(); self.setCentralWidget(w); l=QVBoxLayout(w); l.setSpacing(0); l.setContentsMargins(0,0,0,0)
        
        tb=QFrame(); tb.setFixedHeight(40); tb.setStyleSheet("background:#F9F9F9; border-bottom:1px solid #E5E5EA;")
        tl=QHBoxLayout(tb); tl.setContentsMargins(10,0,10,0); b_set=QPushButton("⚙️ 系统设置 (Settings) ▼"); b_set.setObjectName("BtnToggleSettings"); b_set.clicked.connect(self.t_set)
        tl.addWidget(b_set); tl.addStretch(); l.addWidget(tb)
        
        self.pan=QFrame(); self.pan.setObjectName("SettingsPanel"); self.pan.setFixedHeight(60)
        sl=QHBoxLayout(self.pan); sl.setContentsMargins(20,0,20,0)
        b_add=QPushButton("+ 增加台架"); b_add.setObjectName("BtnAdd"); b_add.setFixedSize(100,36); b_add.clicked.connect(self.add)
        b_rem=QPushButton("- 减少台架"); b_rem.setObjectName("BtnRemove"); b_rem.setFixedSize(100,36); b_rem.clicked.connect(self.rem)
        chk=QCheckBox("仿真 (Sim)"); chk.setStyleSheet("font-weight:bold; color:#007AFF;"); chk.stateChanged.connect(self.sim)
        self.ld=QLabel(os.getcwd()); self.ld.setStyleSheet("color:#8E8E93"); bd=QPushButton("路径"); bd.setObjectName("BtnSecondary"); bd.setFixedSize(100,36); bd.clicked.connect(self.dir)
        sl.addWidget(b_add); sl.addWidget(b_rem); sl.addWidget(chk); sl.addStretch(); sl.addWidget(self.ld); sl.addWidget(bd); l.addWidget(self.pan)
        
        sp=QSplitter(Qt.Orientation.Vertical); sp.setHandleWidth(8); sp.setChildrenCollapsible(False)
        sc=QScrollArea(); sc.setWidgetResizable(True); gw=QWidget(); gw.setObjectName("ScrollContents"); self.g=QGridLayout(gw); self.g.setSpacing(20); self.g.setContentsMargins(20,20,20,20); sc.setWidget(gw); sp.addWidget(sc)
        
        lc=QFrame(); lc.setObjectName("LogContainer"); ll=QVBoxLayout(lc); ll.setContentsMargins(10,10,10,10)
        ll.addWidget(QLabel("System Log", styleSheet="color:#8E8E93; font-weight:bold; font-size:12px;")); self.lg=QTextEdit(); self.lg.setReadOnly(True); ll.addWidget(self.lg); sp.addWidget(lc); sp.setSizes([800,200]); l.addWidget(sp)
        
        self.sig_log.connect(lambda m: self.lg.append(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {m}"))
        self.sts=[]; set_keep_awake(True); self.add()

    def add(self): 
        s=StationWidget(len(self.sts)+1, self.sig_log); 
        self.sts.append(s); 
        self.rlo(); 
        self.sig_log.emit(f"系统: 增加台架 {s.idx}")
    def rem(self): 
        if len(self.sts)<=1 or (self.sts[-1].worker and self.sts[-1].worker.isRunning()): return
        s=self.sts.pop(); s.deleteLater(); self.rlo()
    def rlo(self):
        for i in reversed(range(self.g.count())): self.g.itemAt(i).widget().setParent(None)
        c=len(self.sts); cols=1 if c==1 else (2 if c<=4 else 3)
        for i,s in enumerate(self.sts): self.g.addWidget(s, i//cols, i%cols)
    def t_set(self): self.pan.setVisible(not self.pan.isVisible())
    def sim(self, s): global SIMULATION_MODE; SIMULATION_MODE=(s==2); self.sig_log.emit(f"Sim: {SIMULATION_MODE}")
    def dir(self): d=QFileDialog.getExistingDirectory(); self.ld.setText(d) if d else None; os.chdir(d) if d else None
    def closeEvent(self, e): set_keep_awake(False); [s.stop() for s in self.sts]; e.accept()

if __name__ == '__main__':
    os.environ["QT_SCALE_FACTOR"] = "1"
    if hasattr(Qt.ApplicationAttribute, 'AA_EnableHighDpiScaling'): QApplication.setAttribute(Qt.ApplicationAttribute.AA_EnableHighDpiScaling, True)
    app = QApplication(sys.argv); app.setStyleSheet(IOS_LIGHT_THEME); app.setFont(QFont("Segoe UI", 9))
    w = MainWindow(); w.showMaximized(); sys.exit(app.exec())