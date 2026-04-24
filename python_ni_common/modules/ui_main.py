# -*- coding: utf-8 -*-
import sys
import os
import json
import time
from datetime import datetime
from collections import deque

from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QGridLayout, QLabel, 
                             QLineEdit, QPushButton, QCheckBox, QTextEdit, 
                             QFileDialog, QSplitter, QMessageBox,
                             QScrollArea, QDialog, QComboBox, QTabWidget,
                             QSizePolicy, QFrame, QGraphicsDropShadowEffect, 
                             QListWidget, QListWidgetItem, QProgressBar, QDoubleSpinBox, QGroupBox)
from PyQt6.QtCore import Qt, pyqtSignal, QPropertyAnimation, QEasingCurve, QTimer
from PyQt6.QtGui import QFont, QColor, QPalette, QBrush

import pyqtgraph as pg

# --- 引入模块化后端 ---
from .config_loader import SYS_CONFIG
from .driver import HardwareDriver
from .logic_engine import RecipeEngine

# ============================================================================
# [样式表]
# ============================================================================
IOS_LIGHT_THEME = """
    QWidget { background-color: #F9F9F9; color: #1C1C1E; font-family: "Segoe UI", "Microsoft YaHei"; font-size: 14px; }
    QMainWindow, QWidget#CentralWidget { background-color: #F2F2F7; }
    
    QFrame#SettingsPanel, QFrame#Card, QDialog { 
        background-color: #FFFFFF; border-radius: 12px; border: 1px solid #E5E5EA; 
    }
    
    QLabel { color: #1C1C1E; background-color: transparent; border: none; }
    QLabel#CardTitle { font-size: 20px; font-weight: bold; color: #000000; }
    QLabel#BigValue { font-size: 32px; font-weight: bold; color: #007AFF; }
    
    QLineEdit, QComboBox, QDoubleSpinBox, QTextEdit { 
        background-color: #F2F2F7; border: 1px solid #E5E5EA; border-radius: 8px; 
        padding: 6px 10px; color: #000000; 
    }
    QLineEdit:focus, QTextEdit:focus { border: 1px solid #007AFF; background-color: #FFFFFF; }
    
    QPushButton { 
        border-radius: 8px; padding: 6px 12px; font-weight: 600; 
        border: 1px solid #D1D1D6; background-color: #FFFFFF; color: #1C1C1E; 
    }
    QPushButton:hover { background-color: #F2F2F7; }
    
    QPushButton#BtnPrimary { background-color: #007AFF; color: white; border: none; }
    QPushButton#BtnPrimary:hover { background-color: #0062CC; }
    QPushButton#BtnDanger { background-color: #FF3B30; color: white; border: none; }
    QPushButton#BtnDanger:hover { background-color: #D63027; }
    
    QListWidget { 
        border: 1px solid #E5E5EA; border-radius: 8px; 
        background-color: #F9F9F9; outline: none;
    }
    QListWidget::item { padding: 8px; border-bottom: 1px solid #EEE; color: #555; }
    QListWidget::item:selected { 
        background-color: #E3F2FD; color: #007AFF; border-left: 4px solid #007AFF; font-weight: bold;
    }
    
    /* 指示灯按钮 (DO控制) */
    QPushButton.IndicatorOn { 
        background-color: #34C759; color: white; border: none; font-size: 13px;
    }
    QPushButton.IndicatorOff { 
        background-color: #EEEEEE; color: #999999; border: 1px solid #DDDDDD; font-size: 13px;
    }
    
    QGroupBox {
        font-weight: bold; border: 1px solid #E5E5EA; border-radius: 8px; margin-top: 10px;
    }
    QGroupBox::title { subcontrol-origin: margin; left: 10px; padding: 0 5px; }
"""

STATUS_STYLES = {
    "run": "color: #34C759; font-weight: bold;",
    "stop": "color: #8E8E93; font-weight: bold;",
    "err": "color: #FF3B30; font-weight: bold;",
    "pause": "color: #FF9500; font-weight: bold;",
}

def apply_global_light_theme():
    app = QApplication.instance()
    if not app: return
    app.setStyle("Fusion")
    palette = QPalette()
    palette.setColor(QPalette.ColorRole.Window, QColor("#F2F2F7"))
    palette.setColor(QPalette.ColorRole.WindowText, QColor("#000000"))
    palette.setColor(QPalette.ColorRole.Base, QColor("#FFFFFF"))
    palette.setColor(QPalette.ColorRole.Text, QColor("#000000"))
    palette.setColor(QPalette.ColorRole.Button, QColor("#FFFFFF"))
    palette.setColor(QPalette.ColorRole.ButtonText, QColor("#000000"))
    palette.setColor(QPalette.ColorRole.Highlight, QColor("#007AFF"))
    app.setPalette(palette)
    app.setStyleSheet(IOS_LIGHT_THEME)
    app.setFont(QFont("Segoe UI", 9))


class HardwareConfigDialog(QDialog):
    """
    [硬件配置] 保持不变
    """
    def __init__(self, current_config, parent=None):
        super().__init__(parent)
        self.setWindowTitle("硬件资源映射 (Hardware Mapping)")
        self.resize(1000, 700) 
        self.config = current_config or {}
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("勾选并命名该台架使用的硬件接口："))
        self.tabs = QTabWidget()
        self.tab_dio = QWidget(); self.dio_items = self.create_grid_page(self.tab_dio, "port0/line", 32, "DO/DI", "Valve_1")
        self.tabs.addTab(self.tab_dio, "Digital IO (32)")
        self.tab_ai = QWidget(); self.ai_items = self.create_grid_page(self.tab_ai, "ai", 32, "Analog In", "Pressure_1")
        self.tabs.addTab(self.tab_ai, "Analog Input (32)")
        self.tab_ao = QWidget(); self.ao_items = self.create_grid_page(self.tab_ao, "ao", 4, "Analog Out", "Control_V")
        self.tabs.addTab(self.tab_ao, "Analog Output (4)")
        layout.addWidget(self.tabs)
        
        btn_box = QHBoxLayout(); btn_box.addStretch()
        btn_cancel = QPushButton("取消"); btn_cancel.clicked.connect(self.reject)
        btn_save = QPushButton("保存配置"); btn_save.setObjectName("BtnPrimary"); btn_save.clicked.connect(self.save_config)
        btn_box.addWidget(btn_cancel); btn_box.addWidget(btn_save)
        layout.addLayout(btn_box)
        self.load_from_config()

    def create_grid_page(self, parent_widget, id_prefix, count, title_prefix, name_hint):
        layout = QVBoxLayout(parent_widget)
        scroll = QScrollArea(); scroll.setWidgetResizable(True); scroll.setFrameShape(QFrame.Shape.NoFrame)
        content = QWidget(); grid = QGridLayout(content); grid.setSpacing(15)
        items = [] 
        cols = 4
        for i in range(count):
            item_id = f"{id_prefix}{i}"
            group = QFrame(); group.setStyleSheet("background-color: #F9F9F9; border-radius: 6px; border: 1px solid #E5E5EA;")
            g_lay = QVBoxLayout(group); g_lay.setContentsMargins(8, 8, 8, 8)
            top_row = QHBoxLayout()
            chk = QCheckBox(f"{title_prefix} {i}"); chk.setStyleSheet("font-weight: bold;")
            lbl_id = QLabel(item_id); lbl_id.setStyleSheet("color: #AAA; font-size: 10px;")
            top_row.addWidget(chk); top_row.addStretch(); top_row.addWidget(lbl_id)
            name_edit = QLineEdit(); name_edit.setPlaceholderText(name_hint); name_edit.setStyleSheet("background-color: #FFFFFF;")
            chk.toggled.connect(name_edit.setEnabled); name_edit.setEnabled(False) 
            g_lay.addLayout(top_row); g_lay.addWidget(name_edit)
            grid.addWidget(group, i // cols, i % cols)
            items.append({"id": item_id, "chk": chk, "name": name_edit})
        scroll.setWidget(content); layout.addWidget(scroll)
        return items

    def load_from_config(self):
        def fill(items, data_dict):
            if not data_dict: return
            for item in items:
                uid = item["id"]
                if uid in data_dict:
                    item["chk"].setChecked(True); item["name"].setText(data_dict[uid])
        fill(self.dio_items, self.config.get("dio", {}))
        fill(self.ai_items, self.config.get("ai", {}))
        fill(self.ao_items, self.config.get("ao", {}))

    def save_config(self):
        new_config = {"dio": {}, "ai": {}, "ao": {}}
        def collect(items, target_dict):
            for item in items:
                if item["chk"].isChecked():
                    user_name = item["name"].text().strip()
                    if not user_name: user_name = item["chk"].text()
                    target_dict[item["id"]] = user_name
        collect(self.dio_items, new_config["dio"])
        collect(self.ai_items, new_config["ai"])
        collect(self.ao_items, new_config["ao"])
        self.config = new_config
        self.accept()

    def get_config(self): return self.config


class SettingsDetailDialog(QDialog):
    """
    [工程师控制台 - 重构版]
    Tab 1: 纯粹的手动调试 (曲线 + IO控制)
    Tab 2: 逻辑代码编辑
    """
    def __init__(self, station_card, parent=None):
        super().__init__(parent)
        self.card = station_card
        self.driver = station_card.driver
        self.setWindowTitle(f"Station {self.card.idx} - 工程师控制台 (Engineer Console)")
        self.resize(1100, 750)
        
        self.init_ui()
        
        # 定时刷新曲线
        self.plot_timer = QTimer(self)
        self.plot_timer.timeout.connect(self.refresh_timer_event)
        self.plot_timer.start(50) # 20Hz 刷新，让曲线更流畅

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(0); layout.setContentsMargins(0, 0, 0, 0)
        
        self.tabs = QTabWidget()
        self.tabs.setStyleSheet("""
            QTabBar::tab { height: 40px; width: 150px; font-weight: bold; }
            QTabWidget::pane { border-top: 1px solid #DDD; }
        """)
        
        # Tab 1: 手动调试
        self.tab_monitor = QWidget()
        self.setup_monitor_tab()
        self.tabs.addTab(self.tab_monitor, "手动调试 (Manual & Graph)")
        
        # Tab 2: 逻辑代码
        self.tab_logic = QWidget()
        self.setup_logic_tab()
        self.tabs.addTab(self.tab_logic, "测试逻辑代码 (Recipe JSON)")
        
        layout.addWidget(self.tabs)

    def setup_monitor_tab(self):
        layout = QVBoxLayout(self.tab_monitor)
        layout.setContentsMargins(20, 20, 20, 20); layout.setSpacing(15)
        
        # --- 1. 实时曲线 (占据主要空间) ---
        chart_group = QGroupBox("实时传感器曲线 (Real-time AI)")
        c_lay = QVBoxLayout(chart_group)
        
        self.plot = pg.PlotWidget()
        self.plot.setBackground('#FFFFFF')
        self.plot.getAxis('left').setPen('#8E8E93'); self.plot.getAxis('left').setTextPen('#000000')
        self.plot.getAxis('bottom').setPen('#8E8E93'); self.plot.getAxis('bottom').setTextPen('#000000')
        self.plot.showGrid(x=True, y=True, alpha=0.2)
        self.curve = self.plot.plot(pen=pg.mkPen('#007AFF', width=2))
        c_lay.addWidget(self.plot)
        layout.addWidget(chart_group, stretch=2) # 权重2
        
        # --- 2. 手动控制区 (DO & AO) ---
        ctrl_frame = QFrame()
        ctrl_lay = QHBoxLayout(ctrl_frame); ctrl_lay.setContentsMargins(0,0,0,0); ctrl_lay.setSpacing(20)
        
        # 左侧：DO 控制阵列
        do_group = QGroupBox("执行器控制 (Digital Output)")
        do_inner = QVBoxLayout(do_group)
        self.do_grid = QGridLayout(); self.do_grid.setSpacing(10)
        self.manual_do_btns = {}
        
        do_conf = self.card.hw_config.get("do", {})
        r, c = 0, 0
        for i, (do_id, name) in enumerate(do_conf.items()):
            btn = QPushButton(f"{name}\nOFF")
            btn.setCheckable(True)
            btn.setFixedSize(100, 60)
            btn.setProperty("class", "IndicatorOff") # 初始样式
            btn.clicked.connect(lambda chk, n=name, b=btn: self.manual_toggle_do(n, chk, b))
            
            # 同步当前状态
            current_state = self.driver.do_states.get(name, False)
            btn.setChecked(current_state)
            self.update_btn_style(btn, name, current_state)
            
            self.do_grid.addWidget(btn, r, c)
            self.manual_do_btns[name] = btn
            c += 1; 
            if c > 3: c=0; r+=1
        do_inner.addLayout(self.do_grid)
        do_inner.addStretch()
        ctrl_lay.addWidget(do_group, stretch=3)
        
        # 右侧：AO 控制
        ao_group = QGroupBox("模拟量输出 (Analog Output)")
        ao_inner = QVBoxLayout(ao_group); ao_inner.setSpacing(15)
        self.manual_ao_inputs = {}
        
        ao_conf = self.card.hw_config.get("ao", {})
        if not ao_conf:
            ao_inner.addWidget(QLabel("无配置 AO 通道"))
        
        for ao_id, name in ao_conf.items():
            row = QHBoxLayout()
            row.addWidget(QLabel(f"{name}:"))
            
            spin = QDoubleSpinBox()
            spin.setRange(-10.0, 10.0); spin.setSingleStep(0.1); spin.setDecimals(2)
            spin.setSuffix(" V")
            spin.setFixedWidth(100)
            spin.setFixedHeight(30)
            
            # 获取当前值(如果有缓存)
            curr_val = self.driver.ao_values.get(name, 0.0)
            spin.setValue(curr_val)
            
            spin.valueChanged.connect(lambda v, n=name: self.manual_set_ao(n, v))
            row.addWidget(spin)
            ao_inner.addLayout(row)
            self.manual_ao_inputs[name] = spin
            
        ao_inner.addStretch()
        ctrl_lay.addWidget(ao_group, stretch=2)
        
        layout.addWidget(ctrl_frame, stretch=1) # 权重1
        
        # --- 3. 底部配置入口 ---
        bot_lay = QHBoxLayout()
        btn_hw = QPushButton("硬件 IO 映射配置 (Hardware Mapping)")
        btn_hw.clicked.connect(self.card.open_hw_config)
        bot_lay.addWidget(btn_hw)
        bot_lay.addStretch()
        btn_close = QPushButton("关闭"); btn_close.setFixedWidth(100)
        btn_close.clicked.connect(self.accept)
        bot_lay.addWidget(btn_close)
        
        layout.addLayout(bot_lay)

    def setup_logic_tab(self):
        layout = QVBoxLayout(self.tab_logic)
        layout.setContentsMargins(20, 20, 20, 20)
        
        info = QLabel("在此处直接修改测试流程 (JSON)。修改后点击保存，下次运行测试时生效。")
        info.setStyleSheet("color: #666; margin-bottom: 10px;")
        layout.addWidget(info)
        
        self.code_editor = QTextEdit()
        self.code_editor.setStyleSheet("font-family: Consolas; font-size: 14px; color: #333; background: #FAFAFA;")
        
        try:
            content = json.dumps(SYS_CONFIG.recipe, indent=4, ensure_ascii=False)
            self.code_editor.setText(content)
        except: self.code_editor.setText("{}")
        
        layout.addWidget(self.code_editor)
        
        btn_lay = QHBoxLayout()
        btn_reset = QPushButton("重置 (Reload File)")
        btn_reset.clicked.connect(self.reload_logic)
        
        btn_save = QPushButton("保存并应用 (Save & Apply)")
        btn_save.setObjectName("BtnPrimary")
        btn_save.clicked.connect(self.save_logic)
        
        btn_lay.addWidget(btn_reset)
        btn_lay.addStretch()
        btn_lay.addWidget(btn_save)
        layout.addLayout(btn_lay)

    def refresh_timer_event(self):
        # 刷新曲线
        if len(self.card.data_x) > 0:
            self.curve.setData(self.card.data_x, self.card.data_y)
        
        # 同步外部 DO 状态变化 (比如测试流程中自动改变了IO)
        if self.card.engine and self.card.engine.isRunning():
            for name, btn in self.manual_do_btns.items():
                is_on = self.driver.do_states.get(name, False)
                # 仅更新显示，不触发 clicked 信号
                was_blocked = btn.blockSignals(True)
                btn.setChecked(is_on)
                self.update_btn_style(btn, name, is_on)
                btn.blockSignals(was_blocked)
                # 运行时禁用手动点击
                btn.setEnabled(False)
        else:
            # 非运行时启用
            for btn in self.manual_do_btns.values():
                btn.setEnabled(True)

    def manual_toggle_do(self, name, checked, btn):
        self.driver.write_do(name, checked)
        self.update_btn_style(btn, name, checked)

    def update_btn_style(self, btn, name, is_on):
        if is_on:
            btn.setText(f"{name}\nON")
            btn.setProperty("class", "IndicatorOn")
            btn.setStyleSheet("background-color: #34C759; color: white; border: none;")
        else:
            btn.setText(f"{name}\nOFF")
            btn.setProperty("class", "IndicatorOff")
            btn.setStyleSheet("background-color: #EEEEEE; color: #999999; border: 1px solid #DDDDDD;")

    def manual_set_ao(self, name, val):
        if self.card.engine and self.card.engine.isRunning(): return
        if hasattr(self.driver, 'write_ao'):
            self.driver.write_ao(name, val)

    def save_logic(self):
        txt = self.code_editor.toPlainText()
        try:
            new_recipe = json.loads(txt)
            path = os.path.join(SYS_CONFIG.cfg_path, "recipe_standard.json")
            with open(path, 'w', encoding='utf-8') as f:
                json.dump(new_recipe, f, indent=4, ensure_ascii=False)
            SYS_CONFIG.recipe = new_recipe
            QMessageBox.information(self, "成功", "测试逻辑已更新并保存。")
        except Exception as e:
            QMessageBox.critical(self, "语法错误", f"JSON 格式错误:\n{e}")

    def reload_logic(self):
        SYS_CONFIG.reload()
        content = json.dumps(SYS_CONFIG.recipe, indent=4, ensure_ascii=False)
        self.code_editor.setText(content)


class StationCard(QFrame):
    sig_remove = pyqtSignal(object) 

    def __init__(self, idx, driver, log_signal):
        super().__init__()
        self.setObjectName("Card") 
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.setMinimumHeight(600) 
        
        self.idx = idx
        self.driver = driver
        self.global_log = log_signal
        
        # 默认测试参数 (默认值，可由代码逻辑覆盖)
        self.test_params = {
            "cycles": 350, "target_p": 2.02, "floor_p": 0.02, "max_p": 2.5
        }
        
        # 默认硬件配置
        self.hw_config = {
            "dio": {f"port0/line{i}": f"Valve_{i}" for i in range((idx-1)*8, (idx-1)*8+4)}, 
            "ai": {f"ai{(idx-1)}": "Sys_Pressure"},
            "ao": {}
        }
        
        self.sensor_widgets = {} 
        self.do_widgets = {}     
        self.step_items = []     
        
        self.engine = None
        self.data_x = []
        self.data_y = []
        self.start_time = 0
        
        self.init_ui()
        self.setup_breathing_animation()
        
        self.driver.sig_ai_data.connect(self.update_sensors)
        if hasattr(self.driver, 'sig_do_data'):
            self.driver.sig_do_data.connect(self.update_do_states)

    def setup_breathing_animation(self):
        self.glow_effect = QGraphicsDropShadowEffect(self)
        self.glow_effect.setBlurRadius(40); self.glow_effect.setYOffset(4)
        self.glow_effect.setColor(QColor(0, 0, 0, 25))
        self.setGraphicsEffect(self.glow_effect)
        self.glow_anim = QPropertyAnimation(self.glow_effect, b"color")
        self.glow_anim.setDuration(1500); self.glow_anim.setLoopCount(-1)
        self.glow_anim.setEasingCurve(QEasingCurve.Type.InOutSine)

    def set_glow_state(self, state):
        self.glow_anim.stop()
        if state == "run": self._start_anim(QColor("#34C759"), 3000) 
        elif state == "error": self._start_anim(QColor("#FF3B30"), 800) 
        elif state == "pause": self._start_anim(QColor("#FF9500"), 2000) 
        else: self.glow_effect.setBlurRadius(40); self.glow_effect.setColor(QColor(0, 0, 0, 25))

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
        layout.setSpacing(15); layout.setContentsMargins(20, 20, 20, 20)

        # 1. Header
        h_lay = QHBoxLayout()
        self.lbl_title = QLabel(f"Station {self.idx}"); self.lbl_title.setObjectName("CardTitle")
        h_lay.addWidget(self.lbl_title)
        
        self.in_dev_name = QLineEdit(SYS_CONFIG.hw.get('device_name', 'Dev1'))
        self.in_dev_name.setFixedWidth(60); self.in_dev_name.setPlaceholderText("Dev")
        h_lay.addWidget(QLabel("HW:")); h_lay.addWidget(self.in_dev_name)
        
        h_lay.addStretch()
        self.lbl_status = QLabel("待机"); self.lbl_status.setStyleSheet(STATUS_STYLES["stop"])
        h_lay.addWidget(self.lbl_status)
        
        self.btn_delete = QPushButton("✕"); self.btn_delete.setObjectName("BtnDeleteCard")
        self.btn_delete.setFixedSize(30, 30); self.btn_delete.clicked.connect(lambda: self.sig_remove.emit(self))
        h_lay.addWidget(self.btn_delete) 
        layout.addLayout(h_lay)

        # 2. Main Monitor Area
        monitor_layout = QHBoxLayout()
        
        # Left: Sensors
        sens_frame = QFrame(); sens_frame.setStyleSheet("background-color: #F9F9F9; border-radius: 8px;")
        self.sens_layout = QVBoxLayout(sens_frame)
        self.sens_layout.addWidget(QLabel("SENSORS (AI)"))
        monitor_layout.addWidget(sens_frame, stretch=2)
        
        # Center: Actuators Status (Read-only view here)
        do_frame = QFrame(); do_frame.setStyleSheet("background-color: #F9F9F9; border-radius: 8px;")
        self.do_layout = QVBoxLayout(do_frame)
        self.do_layout.addWidget(QLabel("ACTUATORS STATUS (DO)"))
        self.do_grid = QGridLayout()
        self.do_layout.addLayout(self.do_grid)
        self.do_layout.addStretch()
        monitor_layout.addWidget(do_frame, stretch=3)
        
        # Right: Counters
        stat_frame = QFrame(); stat_frame.setStyleSheet("background-color: #F9F9F9; border-radius: 8px;")
        stat_v = QVBoxLayout(stat_frame)
        stat_v.addWidget(QLabel("STEP TIMER"))
        self.lbl_timer = QLabel("--"); self.lbl_timer.setStyleSheet("font-size: 36px; font-weight: bold; color: #333;")
        self.lbl_timer.setAlignment(Qt.AlignmentFlag.AlignCenter)
        stat_v.addWidget(self.lbl_timer)
        stat_v.addSpacing(10)
        stat_v.addWidget(QLabel("TOTAL CYCLE"))
        self.lbl_progress = QLabel(f"0 / {self.test_params['cycles']}")
        self.lbl_progress.setStyleSheet("font-size: 24px; font-weight: bold; color: #1C1C1E;")
        self.lbl_progress.setAlignment(Qt.AlignmentFlag.AlignCenter)
        stat_v.addWidget(self.lbl_progress)
        stat_v.addStretch()
        monitor_layout.addWidget(stat_frame, stretch=2)
        
        layout.addLayout(monitor_layout)

        # 3. Process Flow
        layout.addWidget(QLabel("PROCESS FLOW MONITOR"))
        self.flow_list = QListWidget()
        self.flow_list.setFixedHeight(180) 
        self.flow_list.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        layout.addWidget(self.flow_list)
        
        # 4. Buttons
        b_lay = QHBoxLayout()
        self.btn_settings = QPushButton("工程师控制台 (Engineer Console)")
        self.btn_settings.setObjectName("BtnSecondary")
        self.btn_settings.clicked.connect(self.open_settings_dialog)
        
        self.btn_start = QPushButton("开始测试"); self.btn_start.setObjectName("BtnPrimary")
        self.btn_start.clicked.connect(self.toggle_test)
        
        self.btn_stop = QPushButton("停止"); self.btn_stop.setObjectName("BtnDanger"); self.btn_stop.setEnabled(False)
        self.btn_stop.clicked.connect(self.stop_test)
        
        b_lay.addWidget(self.btn_settings, stretch=1)
        b_lay.addSpacing(20)
        b_lay.addWidget(self.btn_start, stretch=2)
        b_lay.addWidget(self.btn_stop, stretch=1)
        layout.addLayout(b_lay)
        
        self.refresh_hw_ui()

    def open_hw_config(self):
        dlg = HardwareConfigDialog(self.hw_config, self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            self.hw_config = dlg.get_config()
            self.refresh_hw_ui()
            self.global_log.emit(f"[Station {self.idx}] 硬件配置已更新")

    def open_settings_dialog(self):
        dlg = SettingsDetailDialog(self, self)
        dlg.exec()

    def refresh_hw_ui(self):
        # AI List
        for i in reversed(range(self.sens_layout.count())):
            item = self.sens_layout.itemAt(i)
            if item.widget() and not isinstance(item.widget(), QLabel):
                item.widget().setParent(None)
        self.sensor_widgets = {}
        ai_conf = self.hw_config.get("ai", {})
        for ai_id, name in ai_conf.items():
            row = QHBoxLayout()
            row.addWidget(QLabel(name))
            val_lbl = QLabel("0.00")
            val_lbl.setObjectName("BigValue")
            val_lbl.setAlignment(Qt.AlignmentFlag.AlignRight)
            row.addWidget(val_lbl)
            w = QWidget(); w.setLayout(row)
            self.sens_layout.addWidget(w)
            self.sensor_widgets[ai_id] = val_lbl
        self.sens_layout.addStretch()

        # DO Grid (Read-only indicators on main screen)
        for i in reversed(range(self.do_grid.count())):
            self.do_grid.itemAt(i).widget().setParent(None)
        self.do_widgets = {}
        do_conf = self.hw_config.get("do", {})
        r, c = 0, 0
        for do_id, name in do_conf.items():
            btn = QPushButton(name)
            btn.setFixedSize(80, 40)
            btn.setProperty("class", "IndicatorOff") 
            btn.setFocusPolicy(Qt.FocusPolicy.NoFocus)
            self.do_grid.addWidget(btn, r, c)
            self.do_widgets[name] = btn 
            c += 1
            if c > 3: c=0; r+=1

    def update_sensors(self, data):
        for ai_id, lbl in self.sensor_widgets.items():
            val = data.get(ai_id, 0.0)
            lbl.setText(f"{val:.2f}")
        
        # Buffer for chart
        ai_conf = self.hw_config.get("ai", {})
        if ai_conf:
            first_key = list(ai_conf.keys())[0]
            val = data.get(first_key, 0.0)
            # Always record data if engine running, or just keep a small buffer for manual debug
            self.data_x.append(time.time() - self.start_time)
            self.data_y.append(val)
            if len(self.data_x) > 2000: self.data_x.pop(0); self.data_y.pop(0)

    def update_do_states(self, states):
        for name, btn in self.do_widgets.items():
            is_on = states.get(name, False)
            style = "background-color: #34C759; color: white; border: none;" if is_on else "background-color: #EEE; color: #AAA; border: 1px solid #DDD;"
            btn.setStyleSheet(style)

    def populate_flow_list(self):
        self.flow_list.clear()
        self.step_items = []
        if not self.engine: return
        
        recipe = self.engine.raw_recipe
        for p_idx, phase in enumerate(recipe):
            p_name = phase.get("name", f"Phase {p_idx+1}")
            head = QListWidgetItem(f"== {p_name} ==")
            head.setBackground(QColor("#E0E0E0")); head.setFlags(Qt.ItemFlag.NoItemFlags)
            self.flow_list.addItem(head)
            
            for s_idx, step in enumerate(phase.get("steps", [])):
                desc = f"  [{step['type']}] {step.get('target', '')} {step.get('condition', '')} {step.get('value', '')}"
                item = QListWidgetItem(desc)
                item.setData(Qt.ItemDataRole.UserRole, (p_idx, s_idx))
                self.flow_list.addItem(item)
                self.step_items.append(item)

    def toggle_test(self):
        if self.engine and self.engine.isRunning():
            self.engine.pause_toggle()
            if self.engine.is_paused:
                self.btn_start.setText("继续测试")
                self.btn_start.setStyleSheet("background-color: #34C759; color: white; border: none;")
                self.set_glow_state("pause")
                self.lbl_status.setText("已暂停")
                self.lbl_status.setStyleSheet(STATUS_STYLES["pause"])
            else:
                self.btn_start.setText("暂停测试")
                self.btn_start.setStyleSheet("background-color: #FF9500; color: white; border: none;")
                self.set_glow_state("run")
                self.lbl_status.setText("运行中")
                self.lbl_status.setStyleSheet(STATUS_STYLES["run"])
        else:
            self.start_test()

    def start_test(self):
        run_params = self.test_params.copy()
        run_params["device"] = self.in_dev_name.text()
        run_params["hw_config"] = self.hw_config
        run_params["timeout"] = 90.0

        self.engine = RecipeEngine(self.driver, run_params)
        self.engine.sig_status.connect(self.update_status)
        self.engine.sig_progress.connect(self.update_progress)
        self.engine.sig_finished.connect(self.on_finish)
        self.engine.sig_error.connect(self.on_error)
        
        if hasattr(self.engine, 'sig_step_info'):
            self.engine.sig_step_info.connect(self.update_step_info)
            
        self.engine.sig_status.connect(lambda s: self.global_log.emit(f"[Station {self.idx}] {s}"))
        
        self.data_x = []; self.data_y = []
        self.start_time = time.time()
        self.populate_flow_list()
        
        self.btn_start.setText("暂停测试")
        self.btn_start.setStyleSheet("background-color: #FF9500; color: white; border: none;") 
        self.btn_delete.setVisible(False)
        self.btn_stop.setEnabled(True)
        
        self.set_glow_state("run")
        self.engine.start()

    def stop_test(self):
        if self.engine: self.engine.stop()

    def update_status(self, msg):
        self.lbl_status.setText(msg)
        self.lbl_status.setStyleSheet(STATUS_STYLES["run"])

    def update_progress(self, curr, total):
        self.lbl_progress.setText(f"{curr} / {total}")

    def update_step_info(self, p_idx, s_idx, desc, detail):
        for item in self.step_items:
            if item.data(Qt.ItemDataRole.UserRole) == (p_idx, s_idx):
                self.flow_list.setCurrentItem(item)
                self.flow_list.scrollToItem(item)
                break
        if detail and "s" in detail:
            self.lbl_timer.setText(detail.replace("s", ""))
        elif detail:
            self.lbl_timer.setText(detail)

    def on_error(self, err_msg):
        self.set_glow_state("error")
        self.lbl_status.setText(f"故障: {err_msg}")
        self.lbl_status.setStyleSheet(STATUS_STYLES["err"])

    def on_finish(self):
        self.btn_start.setText("开始测试"); self.btn_start.setObjectName("BtnPrimary"); self.btn_start.setStyleSheet("") 
        self.btn_stop.setEnabled(False)
        self.btn_delete.setVisible(True)
        self.set_glow_state("idle")
        self.lbl_status.setText("测试完成")
        self.lbl_status.setStyleSheet(STATUS_STYLES["stop"])


class MainWindow(QMainWindow):
    sig_log = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        apply_global_light_theme()

        self.setWindowTitle(f"Compressor Lifetime System (Modular Rev 4.1)")
        self.resize(1440, 960)
        self.stations = []
        
        self.driver = HardwareDriver()
        self.driver.setup()
        self.driver.start()
        
        main_w = QWidget(); main_w.setObjectName("CentralWidget")
        self.setCentralWidget(main_w)
        layout = QVBoxLayout(main_w); layout.setSpacing(0); layout.setContentsMargins(0,0,0,0)

        top_bar = QFrame()
        top_bar.setStyleSheet("background-color: #F9F9F9; border-bottom: 1px solid #E5E5EA;")
        top_bar.setFixedHeight(40)
        tb_layout = QHBoxLayout(top_bar); tb_layout.setContentsMargins(10,0,10,0)
        self.btn_toggle = QPushButton("⚙️ 系统设置 (System Settings) ▼")
        self.btn_toggle.setObjectName("BtnToggleSettings")
        self.btn_toggle.clicked.connect(self.toggle_settings)
        tb_layout.addWidget(self.btn_toggle); tb_layout.addStretch()
        layout.addWidget(top_bar)

        self.settings_panel = QFrame()
        self.settings_panel.setObjectName("SettingsPanel")
        self.settings_panel.setFixedHeight(60)
        sp_layout = QHBoxLayout(self.settings_panel); sp_layout.setContentsMargins(20, 0, 20, 0)
        
        self.btn_add = QPushButton(" + 增加台架 ")
        self.btn_add.setObjectName("BtnAdd")
        self.btn_add.setFixedSize(100, 36)
        self.btn_add.clicked.connect(self.add_station)
        
        self.chk_sim = QCheckBox("仿真模式 (Simulation)")
        self.chk_sim.setStyleSheet("font-weight: bold; color: #007AFF;")
        self.chk_sim.setChecked(self.driver.sim_mode)
        self.chk_sim.stateChanged.connect(self.toggle_sim_mode)
        
        self.lbl_dir = QLabel(SYS_CONFIG.settings.get("log_dir", "./logs"))
        self.lbl_dir.setStyleSheet("color: #8E8E93; margin-right: 10px;")
        
        self.btn_dir = QPushButton("更改路径")
        self.btn_dir.setObjectName("BtnSecondary")
        self.btn_dir.setFixedSize(80, 30)
        self.btn_dir.clicked.connect(self.change_log_dir)
        
        sp_layout.addWidget(self.btn_add)
        sp_layout.addSpacing(20)
        sp_layout.addWidget(self.chk_sim)
        sp_layout.addStretch()
        sp_layout.addWidget(self.lbl_dir)
        sp_layout.addWidget(self.btn_dir)
        layout.addWidget(self.settings_panel)

        self.splitter = QSplitter(Qt.Orientation.Vertical)
        self.splitter.setHandleWidth(8); self.splitter.setChildrenCollapsible(False)
        
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        grid_w = QWidget(); grid_w.setObjectName("ScrollContents")
        self.grid = QGridLayout(grid_w); self.grid.setSpacing(20); self.grid.setContentsMargins(20, 20, 20, 20)
        scroll.setWidget(grid_w); self.splitter.addWidget(scroll)

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
        
        self.add_station()

    def toggle_sim_mode(self, state):
        is_sim = (state == 2) 
        self.driver.sim_mode = is_sim
        SYS_CONFIG.settings["simulation_mode"] = is_sim
        self.append_log(f"系统: 模式切换为 {'仿真' if is_sim else '硬件'} (需重启硬件驱动生效)")

    def change_log_dir(self):
        d = QFileDialog.getExistingDirectory(self, "选择日志保存路径", self.lbl_dir.text())
        if d:
            self.lbl_dir.setText(d)
            SYS_CONFIG.settings["log_dir"] = d
            self.append_log(f"系统: 日志路径已更改为 {d}")

    def add_station(self):
        existing_ids = [s.idx for s in self.stations]
        new_idx = 1
        while new_idx in existing_ids: new_idx += 1
        st = StationCard(new_idx, self.driver, self.sig_log)
        st.sig_remove.connect(self.delete_specific_station) 
        self.stations.append(st)
        self.rearrange_layout()
        self.append_log(f"系统: 已增加台架 (ID: {new_idx})")

    def delete_specific_station(self, station_widget):
        if len(self.stations) <= 1:
            QMessageBox.warning(self, "操作无效", "系统至少需要保留一个台架。")
            return
        if station_widget.engine and station_widget.engine.isRunning():
            QMessageBox.critical(self, "禁止删除", f"台架 {station_widget.idx} 正在运行中，请先停止测试后再删除。")
            return
        idx = station_widget.idx
        self.stations.remove(station_widget)
        self.grid.removeWidget(station_widget)
        station_widget.deleteLater()
        self.rearrange_layout()
        self.append_log(f"系统: 已移除台架 (ID: {idx})")

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

    def append_log(self, t):
        self.log.append(f"[{datetime.now().strftime('%H:%M:%S')}] {t}")
        self.log.verticalScrollBar().setValue(self.log.verticalScrollBar().maximum())

    def closeEvent(self, event):
        self.driver.stop()
        for s in self.stations:
            if s.engine: s.engine.stop()
        event.accept()

if __name__ == '__main__':
    os.environ["QT_SCALE_FACTOR"] = "1"
    if hasattr(Qt.ApplicationAttribute, 'AA_EnableHighDpiScaling'): 
        QApplication.setAttribute(Qt.ApplicationAttribute.AA_EnableHighDpiScaling, True)
    app = QApplication(sys.argv)
    apply_global_light_theme()
    w = MainWindow()
    w.showMaximized()
    sys.exit(app.exec())