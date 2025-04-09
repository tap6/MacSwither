#!/bin/bash

# 获取脚本所在目录
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

# 进入脚本所在目录
cd "$DIR"

# 激活虚拟环境
source venv/bin/activate

# 运行程序
python3 gui.py

# 保持终端窗口打开
read -p "按回车键退出..."