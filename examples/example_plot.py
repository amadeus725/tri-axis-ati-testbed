import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))
from ati_testbed.core_functions import Controller, PositionMonitor

try:
    controller = Controller(ip=b'192.168.0.200', local_ip=b'192.168.0.1')
    print("========= 初始化成功 =========")
except Exception as e:
    print(f"初始化失败: {e}")
    sys.exit(1)

try:
    controller.setup()
    controller.zero()
except Exception as e:
    print(f"发生错误: {e}")
    sys.exit(1)

monitor = PositionMonitor(controller)
monitor.show(en_cli=True)

