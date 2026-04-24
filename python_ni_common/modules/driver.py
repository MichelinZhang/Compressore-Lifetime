import nidaqmx
from nidaqmx.constants import LineGrouping, TerminalConfiguration, AcquisitionType
import statistics
from collections import deque
import random
import time
from PyQt6.QtCore import QThread, pyqtSignal
from .config_loader import SYS_CONFIG

class HardwareDriver(QThread):
    sig_ai_data = pyqtSignal(dict)
    sig_do_data = pyqtSignal(dict)
    sig_error = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self.running = True
        self.sim_mode = SYS_CONFIG.settings.get("simulation_mode", True)
        self.pressure_deque = deque(maxlen=4)
        
        self.task_do = None
        self.task_ai = None
        self.task_ao = None # [新增] AO 任务
        
        self.do_states = {} 
        self.ao_values = {} # [新增] AO 值缓存
        self.sim_p_val = 0.0

    def setup(self):
        self.hw_map = SYS_CONFIG.hw
        self.dev = self.hw_map.get("device_name", "Dev1")
        
        # 初始化 DO/AO 缓存
        for port, info in self.hw_map.get("do", {}).items():
            self.do_states[info["name"]] = info.get("default", False)
            
        for chan, info in self.hw_map.get("ao", {}).items(): # [新增]
            self.ao_values[info] = 0.0 # info在这里是用户命名的名称

        if self.sim_mode: return

        try:
            # Setup DO
            self.task_do = nidaqmx.Task()
            lines = sorted(self.hw_map["do"].keys())
            for line in lines:
                self.task_do.do_channels.add_do_chan(f"{self.dev}/{line}")
            self.task_do.start()

            # Setup AI
            self.task_ai = nidaqmx.Task()
            for chan, info in self.hw_map["ai"].items():
                self.task_ai.ai_channels.add_ai_voltage_chan(
                    f"{self.dev}/{chan}", 
                    terminal_config=TerminalConfiguration.RSE,
                    min_val=-10.0, max_val=10.0
                )
            self.task_ai.timing.cfg_samp_clk_timing(
                rate=500, sample_mode=AcquisitionType.CONTINUOUS, samps_per_chan=1000
            )
            self.task_ai.start()
            
            # Setup AO [新增]
            if "ao" in self.hw_map and self.hw_map["ao"]:
                self.task_ao = nidaqmx.Task()
                # 排序以保证写入顺序一致
                ao_chans = sorted(self.hw_map["ao"].keys())
                for chan in ao_chans:
                    self.task_ao.ao_channels.add_ao_voltage_chan(
                        f"{self.dev}/{chan}",
                        min_val=-10.0, max_val=10.0
                    )
                self.task_ao.start()
                
        except Exception as e:
            self.sig_error.emit(f"HW Init Failed: {e}")

    def write_do(self, logical_name, value):
        """控制数字开关"""
        if logical_name not in self.do_states: return
        self.do_states[logical_name] = value
        self.sig_do_data.emit(self.do_states)

        if self.sim_mode:
            self._simulate_physics()
            return

        if self.task_do:
            try:
                sorted_keys = sorted(self.hw_map["do"].keys())
                data = [self.do_states[self.hw_map["do"][k]["name"]] for k in sorted_keys]
                self.task_do.write(data)
            except Exception as e:
                self.sig_error.emit(f"DO Write Error: {e}")

    def write_ao(self, logical_name, value):
        """[新增] 控制模拟输出"""
        # 更新缓存 (这里简化处理，假设逻辑名就是配置里的值)
        # 实际逻辑名映射需反查 hw_map，为简化代码，这里假设 UI 传对名字
        self.ao_values[logical_name] = float(value)
        
        if self.sim_mode: return

        if self.task_ao:
            try:
                # 按照通道定义顺序写入
                sorted_keys = sorted(self.hw_map["ao"].keys())
                # 找出 logical_name 对应的 channel index 或者重组数据
                # 简单起见，每次全部重写
                data = []
                for k in sorted_keys:
                    name = self.hw_map["ao"][k]
                    val = self.ao_values.get(name, 0.0)
                    data.append(val)
                self.task_ao.write(data)
            except Exception as e:
                self.sig_error.emit(f"AO Write Error: {e}")

    def run(self):
        while self.running:
            data_out = {}
            if self.sim_mode:
                time.sleep(0.05)
                self._simulate_physics()
                data_out["Sys_Pressure"] = self._apply_filter(self.sim_p_val + random.uniform(-0.02, 0.02))
            
            elif self.task_ai:
                try:
                    raw_data = self.task_ai.read(number_of_samples_per_channel=nidaqmx.constants.READ_ALL_AVAILABLE)
                    if len(raw_data) > 0:
                        if len(raw_data) >= 3: val = statistics.median(raw_data)
                        else: val = raw_data[-1]
                        
                        p_val = (val + self.hw_map["ai"]["ai0"]["scale_intercept"]) * self.hw_map["ai"]["ai0"]["scale_slope"]
                        p_val = max(0, p_val)
                        final_p = self._apply_filter(p_val)
                        data_out["Sys_Pressure"] = final_p
                except: pass

            self.sig_ai_data.emit(data_out)

    def _apply_filter(self, val):
        self.pressure_deque.append(val)
        avg = sum(self.pressure_deque) / len(self.pressure_deque)
        return 0.0 if avg < 0.02 else avg

    def _simulate_physics(self):
        if self.do_states.get("Compressor") and self.do_states.get("Valve_V1"):
            self.sim_p_val += 0.1
        elif self.do_states.get("Valve_V2") or self.do_states.get("Valve_V3"):
            self.sim_p_val -= 0.2
        else:
            self.sim_p_val -= 0.01
        self.sim_p_val = max(0, min(3.0, self.sim_p_val))

    def stop(self):
        self.running = False
        try:
            if self.task_do: self.task_do.close()
            if self.task_ai: self.task_ai.close()
            if self.task_ao: self.task_ao.close()
        except: pass