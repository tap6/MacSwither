import subprocess
import json
import os
import shutil
from datetime import datetime
from pathlib import Path
import plistlib
import logging
import time

class SystemPatch:
    def __init__(self):
        self.config = self._load_config()
        self.snapshots_dir = Path("snapshots")
        self.setup_logging()

    def setup_logging(self):
        """设置日志记录"""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler('macswitcher.log'),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)

    def _load_config(self):
        """加载配置文件"""
        try:
            with open('config.json', 'r') as f:
                config = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            # 如果配置文件不存在或格式错误，创建默认配置
            config = {
                "BackupTargets":{
                    "plist_files": [
                        "com.apple.dock",
                        ".GlobalPreferences",
                        "com.apple.WindowManager",
                        "com.apple.finder",
                        "com.apple.HIToolbox",
                        "NSGlobalDomain"
                    ]
                },
                "SelfSetting":{
                    "language":"en",
                    "startwithreboot":False,
                    "adding2focus":False
                }
            }
            with open('config.json', 'w') as f:
                json.dump(config, f, indent=4)
            self.logger.info("Created default config.json")
        return config

    def run_cmd(self, cmd):
        """执行命令并返回结果"""
        try:
            result = subprocess.run(cmd, check=True, capture_output=True, text=True)
            self.logger.info(f"Command executed successfully: {' '.join(cmd)}")
            return result.stdout.strip()
        except subprocess.CalledProcessError as e:
            self.logger.error(f"Command failed: {' '.join(cmd)}\nError: {e}\nOutput: {e.output}")
            return f"Error: {e}"

    def restore_plist(self, plist_name, src_dir):
        """从快照目录恢复 plist 文件"""
        try:
            # 处理 .GlobalPreferences 的特殊情况
            if plist_name == ".GlobalPreferences":
                src = os.path.join(src_dir, ".GlobalPreferences.plist")
                dst = os.path.expanduser("~/Library/Preferences/.GlobalPreferences.plist")
            else:
                src = os.path.join(src_dir, f"{plist_name}.plist")
                dst = os.path.expanduser(f"~/Library/Preferences/{plist_name}.plist")
            
            if os.path.exists(src):
                shutil.copy(src, dst)
                self.logger.info(f"Restored {plist_name}.plist")
                
                # 如果是 Dock 设置，需要特殊处理
                if plist_name == "com.apple.dock":
                    # 确保 Dock 设置被正确应用
                    self.run_cmd(["defaults", "read", "com.apple.dock"])
                    time.sleep(1)  # 等待设置生效
                return True
            else:
                self.logger.warning(f"File not found: {src}")
                return False
        except Exception as e:
            self.logger.error(f"Error restoring {plist_name}.plist: {str(e)}")
            return False

    def apply_snapshot(self, snapshot_name):
        """应用快照"""
        try:
            snapshot_dir = self.snapshots_dir / snapshot_name
            if not snapshot_dir.exists():
                raise FileNotFoundError(f"Snapshot {snapshot_name} not found")

            # 获取默认快照路径
            default_snapshot_dir = self.snapshots_dir / "backup_default"
            if not default_snapshot_dir.exists():
                raise FileNotFoundError("Default snapshot not found")

            # 先恢复默认设置
            for plist in self.config["BackupTargets"]["plist_files"]:
                self.restore_plist(plist, default_snapshot_dir)

            # 应用快照中的设置
            for plist in self.config["BackupTargets"]["plist_files"]:
                self.restore_plist(plist, snapshot_dir)

            # 重启相关进程
            
            self.run_cmd(["killall", "Dock"])
            self.run_cmd(["killall", "Finder"])
            self.run_cmd(["killall", "SystemUIServer"])
            self.run_cmd(["killall", "cfprefsd"])
            time.sleep(2)  # 等待进程重启

            self.logger.info(f"✅ Successfully applied snapshot: {snapshot_name}")
            return True

        except Exception as e:
            self.logger.error(f"Error applying snapshot: {str(e)}")
            return False

def main():
    import sys
    if len(sys.argv) < 2:
        print("❌ 用法: python apply_patch.py 快照名称")
    else:
        manager = SystemPatch()
        manager.apply_snapshot(sys.argv[1])

if __name__ == "__main__":
    main()
