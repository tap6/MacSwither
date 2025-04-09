import subprocess
import json
import os
import shutil
from datetime import datetime
from pathlib import Path
import plistlib
import logging

class SystemSnapshot:
    def __init__(self):
        self.config = self._load_config()
        self.snapshots_dir = Path("snapshots")
        self.snapshots_dir.mkdir(exist_ok=True)
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

    def get_system_version(self):
        """获取系统版本"""
        return self.run_cmd(["sw_vers", "-productVersion"])

    def backup_plist(self, plist_name, dest_dir):
        """备份 plist 文件"""
        try:
            # 处理 .GlobalPreferences 的特殊情况
            if plist_name == ".GlobalPreferences":
                src = os.path.expanduser("~/Library/Preferences/.GlobalPreferences.plist")
                dst = os.path.join(dest_dir, ".GlobalPreferences.plist")
            else:
                src = os.path.expanduser(f"~/Library/Preferences/{plist_name}.plist")
                dst = os.path.join(dest_dir, f"{plist_name}.plist")
            
            if os.path.exists(src):
                shutil.copy(src, dst)
                self.logger.info(f"Backed up: {plist_name}.plist")
                return True
            else:
                self.logger.warning(f"File not found: {src}")
                return False
        except Exception as e:
            self.logger.error(f"Error backing up {plist_name}.plist: {str(e)}")
            return False

    def save_snapshot(self, name):
        """保存系统配置快照"""
        snapshot_dir = self.snapshots_dir / name
        snapshot_dir.mkdir(exist_ok=True)
        backup_targets = self.config["BackupTargets"]

        # 获取默认快照路径
        default_snapshot_dir = self.snapshots_dir / "backup_default"

        # 备份 plist 文件
        for plist in backup_targets["plist_files"]:
            self.logger.info(f"Attempting to backup {plist}.plist...")
            success = self.backup_plist(plist, str(snapshot_dir))
            if not success:
                self.logger.error(f"Failed to backup {plist}.plist")

        # 保存元数据
        meta = {
            "name": name,
            "timestamp": datetime.now().isoformat(),
            "systemVersion": self.get_system_version()
        }
        with open(snapshot_dir / "meta.json", "w") as f:
            json.dump(meta, f, indent=2)

        self.logger.info(f"✅ 快照已保存到 {snapshot_dir}")
        return True


def main():
    import sys
    if len(sys.argv) < 2:
        print("❌ 用法: python snapshot.py 配置名称")
    else:
        manager = SystemSnapshot()
        manager.save_snapshot(sys.argv[1])

if __name__ == "__main__":
    main()
