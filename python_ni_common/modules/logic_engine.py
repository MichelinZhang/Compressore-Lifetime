import time
import copy
from PyQt6.QtCore import QThread, pyqtSignal
from .config_loader import SYS_CONFIG

class RecipeEngine(QThread):
    sig_status = pyqtSignal(str)
    sig_progress = pyqtSignal(int, int)
    # [新增] 发送当前步骤信息: (阶段索引, 步骤索引, 步骤描述, 倒计时/目标值)
    sig_step_info = pyqtSignal(int, int, str, str)
    sig_finished = pyqtSignal()
    sig_error = pyqtSignal(str)

    def __init__(self, driver, params_override=None):
        super().__init__()
        self.driver = driver
        self.raw_recipe = SYS_CONFIG.recipe
        self.params = params_override if params_override else {}
        self.total_cycles = self.params.get("cycles", 350)
        
        self.current_cycle = 0
        self.is_paused = False
        self.is_stopped = False
        self.latest_data = {}
        
        self.driver.sig_ai_data.connect(self._update_data)

    def _update_data(self, data):
        self.latest_data = data

    def run(self):
        self.is_stopped = False
        self.current_cycle = 1
        
        while self.current_cycle <= self.total_cycles:
            if self.is_stopped: break
            
            self.sig_progress.emit(self.current_cycle, self.total_cycles)
            self.sig_status.emit(f"Cycle {self.current_cycle} Running")
            
            # 运行配方
            for p_idx, phase in enumerate(self.raw_recipe):
                if not self._run_phase(p_idx, phase):
                    if self.is_stopped: break
            
            self.current_cycle += 1
            
        self.driver.write_do("Compressor", False)
        self.sig_finished.emit()

    def _run_phase(self, phase_idx, phase_config):
        count = phase_config.get("loop_count", 1)
        steps = phase_config.get("steps", [])
        
        for i in range(count):
            if self.is_stopped: return False
            
            for s_idx, step in enumerate(steps):
                # 传递 phase_idx 和 step_idx 给 UI 用于高亮
                if not self._execute_step(phase_idx, s_idx, step):
                    return False
        return True

    def _execute_step(self, p_idx, s_idx, step):
        self._check_pause()
        if self.is_stopped: return False

        stype = step["type"]
        step_val = step.get("value")
        
        # 参数覆盖逻辑
        if stype == "WAIT_ANALOG":
            if step["condition"] == ">=" and "target_p" in self.params:
                step_val = self.params["target_p"]
            elif step["condition"] == "<=" and "floor_p" in self.params:
                step_val = self.params["floor_p"]

        # --- [关键] 通知 UI 当前步骤 ---
        desc = ""
        detail = ""
        if stype == "LOG": desc = f"Log: {step.get('msg')}"
        elif stype == "SET_DO": desc = f"Action: {step['target']} -> {step['value']}"
        elif stype == "WAIT_TIME": 
            desc = "Wait Time"
            detail = f"{step_val}s"
        elif stype == "WAIT_ANALOG": 
            desc = f"Wait {step['target']} {step['condition']}"
            detail = f"{step_val}"
        
        self.sig_step_info.emit(p_idx, s_idx, desc, detail)
        # ---------------------------

        if stype == "LOG":
            pass

        elif stype == "SET_DO":
            self.driver.write_do(step["target"], step["value"])

        elif stype == "WAIT_TIME":
            target = float(step_val)
            start = time.time()
            while time.time() - start < target:
                if self.is_stopped: return False
                self._check_pause()
                # 实时更新倒计时
                remain = target - (time.time() - start)
                self.sig_step_info.emit(p_idx, s_idx, desc, f"{remain:.1f}s")
                time.sleep(0.1)

        elif stype == "WAIT_ANALOG":
            target_key = step["target"]
            limit = float(step_val)
            cond = step["condition"]
            timeout = step.get("timeout", 90.0)
            
            start = time.time()
            while True:
                if self.is_stopped: return False
                self._check_pause()
                
                curr_val = self.latest_data.get(target_key, 0)
                
                # 实时更新等待状态
                self.sig_step_info.emit(p_idx, s_idx, desc, f"Curr: {curr_val:.2f} / Tgt: {limit}")

                if cond == ">=" and curr_val >= limit: break
                if cond == "<=" and curr_val <= limit: break
                
                if time.time() - start > timeout:
                    self.sig_error.emit(f"Wait {target_key} Timeout")
                    return False
                time.sleep(0.05)
                
        elif stype == "LOOP_NESTED":
            sub_count = step["count"]
            sub_steps = step["steps"]
            for _ in range(sub_count):
                for sub_s_idx, sub in enumerate(sub_steps):
                    # 嵌套循环暂时简单映射，避免索引复杂化
                    if not self._execute_step(p_idx, s_idx, sub): return False

        return True

    def _check_pause(self):
        while self.is_paused:
            if self.is_stopped: break
            time.sleep(0.1)

    def pause_toggle(self):
        self.is_paused = not self.is_paused
    
    def stop(self):
        self.is_stopped = True