from ctypes import *
import os
import time
import numpy as np
from struct import unpack
import functools
import threading
import sys
from collections import deque
import nidaqmx
import atiiaftt
import pyqtgraph as pg
import csv
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
            self.dll.GA_EncOn(i)
            self.dll.GA_AxisOn(i)
            self.dll.GA_PrfTrap(i) # 默认初始化为点位模式
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
                for j in range(1, 5):
                    self.dll.GA_PrfTrap(j) # 切回点位模式
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
            self.dll.GA_PrfTrap(i) # 防止被pt模式替代
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
    def move_pt_trajectory(self, trajectory_points, wait: bool = True):
        """
        执行 PT (Position-Time) 连续轨迹运动 (带分块防溢出机制)
        """
        pass
    
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
    """ 基于 NI DAQ 和 atiiaftt 的力觉传感器类 """
    
    def __init__(self, cal_file=None, dev_name='Dev1'):
        """
        初始化传感器和采集卡
        :param cal_file: 传感器的标定文件路径 (默认 'FT60628.cal')
        :param dev_name: NI 采集卡的设备名称 (默认 'Dev1')
        """
        print("[ATISensor] 正在初始化采集卡与传感器...")
        
        if cal_file is None:
            cal_file = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../data/FT60628.cal"))
            print(cal_file)
        
        # 1. 初始化 NI DAQ 任务
        self.task = nidaqmx.Task()
        # ATI 传感器通常有 6 个通道 (ai0 到 ai5)
        for i in range(6):
            self.task.ai_channels.add_ai_voltage_chan(f'{dev_name}/ai{i}')   
            
        # 2. 初始化 ATI 转换库
        self.sensor = atiiaftt.FTSensor()
        self.sensor.createCalibration(cal_file, 1)
        
        # 设置工具坐标系变换 (根据您原代码保留)
        self.sensor.setToolTransform([0, 0, 45, 0, 0, 0], 
                                     atiiaftt.FTUnit.DIST_MM, 
                                     atiiaftt.FTUnit.ANGLE_DEG)
        
        # 3. 采集初始偏置 (Bias / 归零)
        print("[ATISensor] 正在采集零点偏置，请勿触碰传感器...")
        DAQ_bias = []
        for i in range(10):
            DAQ_bias.append(self.task.read())
            time.sleep(0.01)
            
        mean_bias = np.mean(DAQ_bias, axis=0).tolist()
        self.sensor.bias(mean_bias)
        print("[ATISensor] 初始化完成，已成功归零！")

    def get_force(self):
        """
        读取并转换力/力矩数据
        :return: 包含 6 个元素的 numpy 数组 [Fx, Fy, Fz, Tx, Ty, Tz]
        """
        # 连续读取 5 次求平均，用于软件滤波，降低噪声
        force = np.zeros((5, 6))
        for i in range(5):
            # 1. 从采集卡读取 6 个通道的原始电压值
            raw_voltages = self.task.read()
            # 2. 将电压值转换为 力/力矩
            force[i, :] = self.sensor.convertToFt(raw_voltages)
            
        return np.mean(force, axis=0)

    def close(self):
        """ 释放 DAQ 资源 """
        if hasattr(self, 'task'):
            self.task.close()
            print("[ATISensor] 采集卡任务已关闭。")

    def __del__(self):
        self.close()

class ForceMonitor:
    """ ATI 力觉传感器实时监控可视化界面 """
    def __init__(self, sensor: ATISensor, buffer_size: int = 2000):
        self.sensor = sensor
        self.data_deque = deque(maxlen=buffer_size)
        self.stop_event = threading.Event()

    def _data_worker(self):
        # 力觉数据刷新率可以设置高一点，这里设为 50Hz
        target_fps = 50 
        target_dt = 1.0 / target_fps
        start_time = time.perf_counter()
        next_wake_time = time.perf_counter() + target_dt
        
        while not self.stop_event.is_set():
            try:
                # 获取力觉数据 [Fx, Fy, Fz, Tx, Ty, Tz]
                force_data = self.sensor.get_force()
                if force_data is not None:
                    curr_t = time.perf_counter() - start_time
                    # 我们提取时间 t 以及前三个维度的力 Fx, Fy, Fz
                    record = np.array([curr_t, force_data[0], force_data[1], force_data[2]])
                    self.data_deque.append(record)
                
                now = time.perf_counter()
                sleep_time = next_wake_time - now
                if sleep_time > 0:
                    time.sleep(sleep_time)
                next_wake_time += target_dt
            except Exception as e:
                print(f"力觉数据读取异常：{e}")
                break

    def show(self):
        # 防止重复创建 QApplication
        app = QtWidgets.QApplication.instance()
        if app is None:
            app = QtWidgets.QApplication(sys.argv)
            
        win = pg.GraphicsLayoutWidget(show=True, title="ATI 力觉实时监控")
        win.resize(800, 600)
        
        plot = win.addPlot(title="ATI Sensor Force (Fx, Fy, Fz)")
        plot.addLegend()
        plot.showGrid(x=True, y=True)
        
        # 使用不同颜色区分 Fx, Fy, Fz
        curve_fx = plot.plot(pen=pg.mkPen('r', width=2), name='Fx')
        curve_fy = plot.plot(pen=pg.mkPen('g', width=2), name='Fy')
        curve_fz = plot.plot(pen=pg.mkPen('b', width=2), name='Fz')
        plot.setLabel('bottom', 'Time', units='s')
        plot.setLabel('left', 'Force', units='N')

        def update_plot():
            if len(self.data_deque) > 0:
                data_np = np.array(self.data_deque)
                t_axis = data_np[:, 0]
                curve_fx.setData(x=t_axis, y=data_np[:, 1])
                curve_fy.setData(x=t_axis, y=data_np[:, 2])
                curve_fz.setData(x=t_axis, y=data_np[:, 3])

        timer = QtCore.QTimer()
        timer.timeout.connect(update_plot)
        timer.start(20) # 20ms 刷新一次界面 (50Hz)

        def on_about_to_quit():
            self.stop_event.set()
            print("\n[系统] 力觉监控 GUI 已关闭。")
            
        app.aboutToQuit.connect(on_about_to_quit)

        # 启动后台数据采集线程
        t_data = threading.Thread(target=self._data_worker, daemon=True)
        t_data.start()

        sys.exit(app.exec())


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

class ProcessLogger:
    """ 机床运动与力觉同步记录器 """
    def __init__(self, controller, ati_sensor):
        self.controller = controller
        self.ati = ati_sensor
        self.is_logging = False
        self.recorded_data = []

    def _record_worker(self, record_fps):
        """ 后台记录线程 """
        target_dt = 1.0 / record_fps
        start_time = time.perf_counter()
        
        while self.is_logging:
            loop_start = time.perf_counter()
            
            try:
                # 1. 获取当前时间
                t = loop_start - start_time
                
                # 2. 获取力觉数据
                force = self.ati.get_force()
                
                # 3. 获取机床实时坐标
                pos = self.controller.position(verbose=False)
                
                # 4. 存入内存列表
                row = [t] + list(force) + pos
                self.recorded_data.append(row)
                
            except Exception as e:
                print(f"记录异常: {e}")
                
            # 控制记录频率
            elapsed = time.perf_counter() - loop_start
            sleep_time = target_dt - elapsed
            if sleep_time > 0:
                time.sleep(sleep_time)

    def start(self, record_fps=100):
        """ 开始后台记录 """
        self.recorded_data = []  # 清空历史数据
        self.is_logging = True
        self.thread = threading.Thread(target=self._record_worker, args=(record_fps,), daemon=True)
        self.thread.start()
        print(f"[Logger] 开始后台同步记录，频率: {record_fps}Hz")

    def stop_and_save(self, filename="process_data.csv"):
        """ 停止记录并保存为 CSV 文件 """
        self.is_logging = False
        if hasattr(self, 'thread'):
            self.thread.join() # 等待最后一次记录完成
            
        print(f"[Logger] 停止记录，正在保存 {len(self.recorded_data)} 行数据...")
        
        with open(filename, 'w', newline='') as f:
            writer = csv.writer(f)
            # 写入表头：时间, 6个力, 3个坐标(X,Y,Z)
            writer.writerow(['Time(s)', 'Fx', 'Fy', 'Fz', 'Tx', 'Ty', 'Tz', 'PosX', 'PosY', 'PosZ'])
            writer.writerows(self.recorded_data)
            
        print(f"[Logger] 数据已成功保存至 {filename}")
