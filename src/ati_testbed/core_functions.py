from ctypes import *
import os
import time
import numpy as np
from struct import unpack
import functools
import threading
import sys
from collections import deque
import pyqtgraph as pg
from pyqtgraph.Qt import QtCore, QtWidgets

def _requires_init(func):
    @functools.wraps(func)
    def wrapper(self, *args, **kwargs):
        if not self.is_initialized:
            raise RuntimeError(f"请先完成 setup() 初始化，再调用 {func.__name__}")
        return func(self, *args, **kwargs)
    return wrapper

class Controller:
    """ 运动控制卡封装 """
    def __init__(self, ip=b"192.168.0.200", local_ip=b"192.168.0.1"):
        self.ip = ip
        self.local_ip = local_ip
        self.dll = self._load_gas_dll()
        self.is_initialized = False

    def _load_gas_dll(self):
        current_dir = os.path.dirname(os.path.abspath(__file__))
        dll_path = os.path.join(current_dir, "GAS.dll")
        
        if not os.path.exists(dll_path):
            raise FileNotFoundError(f"核心依赖库缺失：{dll_path}")
            
        try:
            return CDLL(dll_path)
        except Exception as e:
            raise RuntimeError(f"加载 GAS.dll 失败: {e}")

    def setup(self):
        """板卡初始化与安全系统配置"""
        a = self.dll.GA_OpenByIP(self.ip, self.local_ip, 0, 0)
        print('打开板卡GA_Open返回值:', a)
        if a != 0:
            raise RuntimeError(f'板卡打开失败，错误码：{a}，请检查电源和网线')
        a = self.dll.GA_Reset()
        print('复位板卡GA_Reset返回值:', a, '\n')
        
        for i in range(1, 5, 1):
            self.dll.GA_LmtsOn(i, -1)
            self.dll.GA_AxisOn(i)
            self.dll.GA_SetAxisBand(i, c_int(20), 10)
            
        self.dll.GA_LmtSns(255)
        self.dll.GA_EStopSetIO(0, 0, 1, 10)
        self.dll.GA_EStopOnOff(1)
        self.is_initialized = True
        print("初始化成功")

    @_requires_init
    def zero(self):
        """ 回零操作 """
        # 设置轴 1-4 回零参数
        for i in range(1, 5, 1):
            self.dll.GA_HomeSetPrmSingle(i, 1, 0, 0, c_double(20.0), c_double(1.0), c_double(1.0), c_double(0.1), 0, 0, 0)
        print('开始回零')
        
        for i in range(1, 5):
            self.dll.GA_HomeStart(i)
            
        while True:
            m = 1
            for i in range(1, 5, 1):
                nHomeSts = c_short(0)
                lHomeLocateAbsPos = c_int32(0)
                lZCaptureAbsPos = c_int32(0)
                lZCaptureDisToSensor = c_int32(0)
                self.dll.GA_HomeGetSts(i, byref(nHomeSts), byref(lHomeLocateAbsPos), byref(lZCaptureAbsPos), byref(lZCaptureDisToSensor))
                if nHomeSts.value == 2:
                    m = i
                else:
                    break
            if m == 4:
                time.sleep(1)
                self.dll.GA_ZeroPos(1, 4)
                print('回零结束')
                break
            time.sleep(0.05)

    @_requires_init
    def move(self, x: float, y: float, z: float, vel: float = 20.0, wait: bool = True):
        """ 根据毫米坐标绝对/相对运动 (以具体逻辑为准) 
        参数 vel: 目标移动速度 (默认 20.0 毫米每秒)
        参数 wait: 是否阻塞等待该运动执行完毕
        """

        if x < 0 or y < 0 or z < 0:
            raise ValueError(f"目标坐标不能为负数，输入值：x={x}, y={y},z={z}")
        
        m = [x * 2000, x * 2000, z * 2000, y * 2000] # 毫米到脉冲映射
        vel_spike = 2 * vel #  1 毫米/秒 = 2 脉冲/毫秒
        for i in range(1, 5, 1):
            self.dll.GA_EncOn(i)
            self.dll.GA_AxisOn(i)
            self.dll.GA_PrfTrap(i)
            self.dll.GA_SetTrapPrmSingle(i, c_double(1.0), c_double(1.0), c_double(0.0), 0)
            self.dll.GA_SetPos(i, c_int64(int(m[i-1])))
            self.dll.GA_SetVel(i, c_double(vel_spike))
        self.dll.GA_Update(15)

        if wait:
            while True:
                AXIS_STATUS_ARRIVE = 0x00000800
                status_array = (c_long * 4)()
                ret_code = self.dll.GA_GetSts(1, status_array, 4, None)
                all_arrived = False 
                if ret_code == 0:
                    all_arrived = True
                    for i in range(4):
                        if not(status_array[i] & AXIS_STATUS_ARRIVE):
                            all_arrived = False
                if all_arrived:
                    break

    @_requires_init
    def position(self, verbose: bool = True):
        """ 提取当前坐标信息 """
        n = [0, 0, 0, 0]
        for i in range(1, 5, 1):
            dAxisEncPos = c_double(0.0)
            self.dll.GA_GetAxisEncPos(i, byref(dAxisEncPos), 1, 0)
            n[i-1] = dAxisEncPos.value
        
        if verbose:
            print(f'1-4轴脉冲值:{n[0]},{n[1]},{n[2]},{n[3]}')
            print(f'实时坐标:{(n[0]+n[1])/4000},{n[3]/2000},{n[2]/2000}')
        n3 = [(n[0]+n[1])/4000,n[3]/2000,n[2]/2000]
        return n3

class ATISensor:
    """ 力觉传感器对象 """
    def __init__(self, opto_device):
        self.opto = opto_device
        
    def get_force(self):
        while True:
            data = self.opto.read(4)
            if len(data) < 4:
                time.sleep(0.005)
                continue
                
            header = unpack('BBBB', data)
            if header == (170, 7, 8, 10):
                payload = self.opto.read(12)
                if len(payload) < 12:
                    continue
                    
                counter = unpack('>H', payload[0:2])[0]
                status = unpack('>H', payload[2:4])[0]
                xyz = unpack('>hhh', payload[4:10])
                checksum = unpack('>H', payload[10:12])[0]
                
                force = np.array(xyz, dtype=float) / 16038 * 40.0
                force[0] -= (-11.2 / 1000.0 * 9.8)
                force[1] -= (+11.0 / 1000.0 * 9.8)
                force[2] -= (-23.0 / 1000.0 * 9.8)
                break
        return force

class PositionMonitor:
    """ 控制器位置实时监控可视化界面 """
    def __init__(self, controller: Controller, buffer_size: int = 10000):
        self.controller = controller
        self.data_deque = deque(maxlen=buffer_size)
        self.stop_event = threading.Event()

    def _data_worker(self):
        target_fps = 30
        target_dt = 1.0 / target_fps
        start_time = time.perf_counter()
        next_wake_time = time.perf_counter() + target_dt
        
        while not self.stop_event.is_set():
            try:
                curr = self.controller.position(verbose=False)
                if curr is not None:
                    curr_t = time.perf_counter() - start_time
                    record = np.insert(curr, 0, curr_t)
                    self.data_deque.append(record)
                
                now = time.perf_counter()
                sleep_time = next_wake_time - now
                if sleep_time > 0:
                    time.sleep(sleep_time)
                else:
                    pass
                next_wake_time += target_dt
            except Exception as e:
                print(f"数据读取异常：{e}")
                break

    def _cli_worker(self, app):
        time.sleep(0.5) 
        while not self.stop_event.is_set():
            try:
                user_input = input('请输入距离 xyz[mm] (输入 q 退出): ')
                if self.stop_event.is_set():
                    break
                if user_input.strip().lower() == 'q':
                    print("收到退出指令，正在关闭系统...")
                    self.stop_event.set()
                    QtCore.QMetaObject.invokeMethod(app, "quit", QtCore.Qt.QueuedConnection)
                    break
                    
                x, y, z = map(float, user_input.split())
                self.controller.move(x, y, z)
            except ValueError:
                print("\n[错误] 请输入有效的数字坐标，例如: 10 20 30\n请输入距离 xyz[mm] (输入 q 退出): ", end="")
            except Exception as e:
                print(f"【运行异常导致退出】: {e}")
                self.stop_event.set()
                QtCore.QMetaObject.invokeMethod(app, "quit", QtCore.Qt.QueuedConnection)
                break

    def show(self, en_cli = False):
        app = QtWidgets.QApplication(sys.argv)
        win = pg.GraphicsLayoutWidget(show=True, title="实时硬件监控")
        win.resize(800, 600)
        
        plot = win.addPlot(title="Controller Position (X, Y, Z)")
        plot.addLegend()
        plot.showGrid(x=True, y=True)
        
        curve_x = plot.plot(pen=pg.mkPen('r', width=2), name='X Axis')
        curve_y = plot.plot(pen=pg.mkPen('g', width=2), name='Y Axis')
        curve_z = plot.plot(pen=pg.mkPen('b', width=2), name='Z Axis')
        plot.setLabel('bottom', 'Time', units='s')
        plot.setLabel('left', 'Position', units='mm')

        def update_plot():
            if len(self.data_deque) > 0:
                data_np = np.array(self.data_deque)
                t_axis = data_np[:, 0]
                curve_x.setData(x=t_axis, y=data_np[:, 1])
                curve_y.setData(x=t_axis, y=data_np[:, 2])
                curve_z.setData(x=t_axis, y=data_np[:, 3])

        timer = QtCore.QTimer()
        timer.timeout.connect(update_plot)
        timer.start(20)

        def on_about_to_quit():
            self.stop_event.set()
            print("\n[系统] GUI 已关闭。请在控制台按回车键彻底退出...")
            
        app.aboutToQuit.connect(on_about_to_quit)

        t_data = threading.Thread(target=self._data_worker, daemon=True)
        t_data.start()

        if en_cli:
            t_cli = threading.Thread(target=self._cli_worker, args=(app,), daemon=True)
            t_cli.start()

        sys.exit(app.exec())
