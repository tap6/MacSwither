#!/usr/bin/env python3

import wx
import os
import json
from pathlib import Path
from snapshot import SystemSnapshot
# from rollback import RollbackManager # Removed import
import logging

class MacSwitcherFrame(wx.Frame):
    def __init__(self):
        super().__init__(parent=None, title='MacSwitcher', size=(600, 400))
        
        # 设置日志
        self.setup_logging()
        
        # 创建主面板
        self.panel = wx.Panel(self)
        
        # 创建垂直布局
        self.main_sizer = wx.BoxSizer(wx.VERTICAL)
        
        # 添加快照列表
        self.snapshot_list = wx.ListBox(self.panel, style=wx.LB_SINGLE)
        self._refresh_snapshot_list()
        
        # 创建按钮
        self.create_btn = wx.Button(self.panel, label='创建新快照')
        self.apply_btn = wx.Button(self.panel, label='应用选中快照')
        self.delete_btn = wx.Button(self.panel, label='删除选中快照')
        # self.rollback_btn = wx.Button(self.panel, label='回滚到上一个版本') # Removed button
        
        # 绑定事件
        self.create_btn.Bind(wx.EVT_BUTTON, self.on_create)
        self.apply_btn.Bind(wx.EVT_BUTTON, self.on_apply)
        self.delete_btn.Bind(wx.EVT_BUTTON, self.on_delete)
        # self.rollback_btn.Bind(wx.EVT_BUTTON, self.on_rollback) # Removed binding
        
        # 添加控件到布局
        self.main_sizer.Add(wx.StaticText(self.panel, label="系统配置快照列表:"), 0, wx.ALL, 5)
        self.main_sizer.Add(self.snapshot_list, 1, wx.ALL | wx.EXPAND, 5)
        
        # 创建按钮布局
        button_sizer = wx.BoxSizer(wx.HORIZONTAL)
        button_sizer.Add(self.create_btn, 0, wx.ALL, 5)
        button_sizer.Add(self.apply_btn, 0, wx.ALL, 5)
        button_sizer.Add(self.delete_btn, 0, wx.ALL, 5)
        # button_sizer.Add(self.rollback_btn, 0, wx.ALL, 5) # Removed button from sizer
        
        self.main_sizer.Add(button_sizer, 0, wx.ALIGN_CENTER)
        
        # 设置面板布局
        self.panel.SetSizer(self.main_sizer)
        
        # 创建状态栏
        self.CreateStatusBar()
        self.SetStatusText("就绪")
        
        # 居中显示窗口
        self.Centre()
        
        # 检查首次运行
        self._check_first_run()
        
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
        
    def _check_first_run(self):
        """检查是否是首次运行，如果是则提示创建默认快照"""
        snapshots_dir = Path("snapshots")
        default_snapshot = snapshots_dir / "backup_default"
        
        if not default_snapshot.exists():
            dialog = wx.MessageDialog(
                self,
                "首次运行需要保存当前系统配置作为默认快照。\n是否现在创建默认快照？",
                "创建默认快照",
                wx.YES_NO | wx.ICON_QUESTION
            )
            if dialog.ShowModal() == wx.ID_YES:
                try:
                    snapshot = SystemSnapshot()
                    if snapshot.save_snapshot("backup_default"):
                        self.SetStatusText("默认快照创建成功")
                        self._refresh_snapshot_list()
                    else:
                        wx.MessageBox("创建默认快照失败，请检查日志", "错误", wx.OK | wx.ICON_ERROR)
                except Exception as e:
                    self.logger.error(f"创建默认快照失败: {str(e)}")
                    wx.MessageBox(f"创建默认快照失败: {str(e)}", "错误", wx.OK | wx.ICON_ERROR)
            dialog.Destroy()
        
    def _refresh_snapshot_list(self):
        """刷新快照列表"""
        self.snapshot_list.Clear()
        snapshots_dir = Path("snapshots")
        if snapshots_dir.exists():
            for item in snapshots_dir.iterdir():
                if item.is_dir():
                    # 如果是默认快照，添加特殊标记
                    if item.name == "backup_default":
                        self.snapshot_list.Append(f"{item.name} (#base)")
                    else:
                        self.snapshot_list.Append(item.name)
                    
    def on_create(self, event):
        """创建新快照"""
        dialog = wx.TextEntryDialog(self, "请输入新快照名称:", "创建快照")
        if dialog.ShowModal() == wx.ID_OK:
            snapshot_name = dialog.GetValue()
            if snapshot_name:
                if snapshot_name == "backup_default":
                    wx.MessageBox("不能使用 'backup_default' 作为快照名称", "错误", wx.OK | wx.ICON_ERROR)
                    return
                    
                try:
                    snapshot = SystemSnapshot()
                    if snapshot.save_snapshot(snapshot_name):
                        self._refresh_snapshot_list()
                        self.SetStatusText(f"快照 '{snapshot_name}' 创建成功")
                    else:
                        wx.MessageBox("创建快照失败，请检查日志", "错误", wx.OK | wx.ICON_ERROR)
                except Exception as e:
                    self.logger.error(f"创建快照失败: {str(e)}")
                    wx.MessageBox(f"创建快照失败: {str(e)}", "错误", wx.OK | wx.ICON_ERROR)
        dialog.Destroy()
        
    def on_apply(self, event):
        """应用选中快照"""
        selection = self.snapshot_list.GetSelection()
        if selection == wx.NOT_FOUND:
            wx.MessageBox("请先选择一个快照", "提示", wx.OK | wx.ICON_INFORMATION)
            return

        snapshot_name = self.snapshot_list.GetString(selection)
        if snapshot_name.endswith(" (#base)"):
            snapshot_name = "backup_default"

        try:
            import subprocess
            result = subprocess.run(
                ["python3", "apply.py", snapshot_name],
                capture_output=True,
                text=True
            )

            if result.returncode == 0:
                self.SetStatusText(f"✅ 快照 '{snapshot_name}' 已应用")
                #wx.MessageBox(f"快照 '{snapshot_name}' 应用成功", "成功", wx.OK | wx.ICON_INFORMATION)
                # 提示应用成功，并且询问是否退出登陆macOS用户以生效前台调度/鼠标滚动等高级别设置
                dialog=wx.MessageDialog(self, f"✅ 快照 '{snapshot_name}' 应用成功！\n\n相关设置已生效！但「前台调度」「鼠标滚动」等高级别设置需要重启/注销后生效，若您未涉及修改「除dock以外」点否忽略即可😃\n\n\n您的工作窗口不会消失，只需待会☑️勾选恢复窗口，但请您保存好当前的工作数据。\n\n请问是否立刻退出登陆（注销）？", "成功", wx.YES_NO | wx.ICON_QUESTION)
                # 若qq等软件导致了注销等中断，则需要使用「command + alt + esc」来结束qq软件
                if dialog.ShowModal()==wx.ID_YES:
                    os.system("osascript -e 'tell application \"System Events\" to log out'")
                    dialog.Destroy()
                    self.Close()
                else:
                    dialog.Destroy()
            else:
                self.SetStatusText(f"❌ 应用快照失败")
                wx.MessageBox(f"应用失败：\n{result.stderr}", "错误", wx.OK | wx.ICON_ERROR)

        except Exception as e:
            self.logger.error(f"无法执行快照应用命令：{str(e)}")
            wx.MessageBox(f"无法执行快照应用命令：{str(e)}", "错误", wx.OK | wx.ICON_ERROR)
            
    def on_delete(self, event):
        """删除选中快照"""
        selection = self.snapshot_list.GetSelection()
        if selection == wx.NOT_FOUND:
            wx.MessageBox("请先选择一个快照", "提示", wx.OK | wx.ICON_INFORMATION)
            return
            
        snapshot_name = self.snapshot_list.GetString(selection)
        # 移除 "(默认备份)" 标记
        if snapshot_name.endswith(" (#base)"):
            snapshot_name = snapshot_name[:-8]
            
        if wx.MessageBox(f"确定要删除快照 '{snapshot_name}' 吗？", "确认", 
                        wx.YES_NO | wx.NO_DEFAULT | wx.ICON_QUESTION) == wx.YES:
            try:
                import shutil
                shutil.rmtree(Path("snapshots") / snapshot_name)
                self._refresh_snapshot_list()
                self.SetStatusText(f"快照 '{snapshot_name}' 已删除")
            except Exception as e:
                self.logger.error(f"删除快照失败: {str(e)}")
                wx.MessageBox(f"删除快照失败: {str(e)}", "错误", wx.OK | wx.ICON_ERROR)

class MacSwitcherApp(wx.App):
    def OnInit(self):
        frame = MacSwitcherFrame()
        frame.Show()
        return True

if __name__ == '__main__':
    app = MacSwitcherApp()
    app.MainLoop()