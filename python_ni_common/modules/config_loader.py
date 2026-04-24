import json
import os
import sys

class ConfigManager:
    def __init__(self):
        # 获取当前文件所在目录的上级目录 (即 python_ni_common)
        self.root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.cfg_path = os.path.join(self.root, "config")
        self.reload()

    def reload(self):
        self.hw = self._load("hardware.json")
        self.recipe = self._load("recipe_standard.json")
        # [修复] 修正文件名 settings.json -> setting.json
        self.settings = self._load("setting.json") 

    def _load(self, name):
        try:
            path = os.path.join(self.cfg_path, name)
            if not os.path.exists(path):
                print(f"Warning: Config file not found: {path}")
                return {}
            with open(path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"Error loading {name}: {e}")
            return {}

SYS_CONFIG = ConfigManager()