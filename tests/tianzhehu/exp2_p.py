import sys
import os
import numpy as np
import threading
import time

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../src')))
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

def run_experiment(controller):
    control_freq = [2, 3, 5, 8, 10, 20, 30, 50, 100] # Hz
    radius = 40 # [mm]
    velo = 20 # [mm/s]
    omega = velo / radius # [rad/s]

    controller.move(20,0,60)

    for f in control_freq:
        pos_list = [(-radius*np.cos(omega*i/f)+60, radius*np.sin(omega*i/f)+60) for i in range(1, int(f*2*np.pi/omega))]
        dt = 1/f
        for cx, cz in pos_list:
            cv = 2*radius*np.sin(0.5*omega/f)*f
            cur_time = time.perf_counter()
            controller.move(cx, 0, cz, vel=cv, wait=False)
            move_time = time.perf_counter()
            if move_time-cur_time < dt:
                time.sleep(dt + cur_time - move_time)
            else:
                raise SystemError

exp = threading.Thread(target=run_experiment,args=(controller,), daemon=True)
exp.start()

monitor = PositionMonitor(controller)
monitor.show()