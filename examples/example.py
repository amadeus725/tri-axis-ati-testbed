import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))
from ati_testbed.core_functions import Controller

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

while True:
    try:
        user_input = input('请输入距离 xyz[mm] (输入 q 退出): ')
        if user_input.strip().lower() == 'q':
            break
        x, y, z = map(float, user_input.split())
        controller.move(x, y, z)
        controller.position()
        
    except ValueError:
        print("请输入有效的数字坐标，例如: 10 20 30")
    except Exception as e:
        print(f"【运行异常导致退出】: {e}")
        break
