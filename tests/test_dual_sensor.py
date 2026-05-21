import sys
import os
import threading
import time
import serial
from pyqtgraph.Qt import QtWidgets, QtCore

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))
from ati_testbed.core_functions import ATISensor, Controller, ProcessLogger
import csv

# 用于保存最新收到的串口数据
latest_serial_data = "NULL"

def read_serial_data():
    """在独立线程中读取串口数据"""
    global latest_serial_data
    try:
        # 如果波特率非常高，例如 2000000，使用它以匹配几百Hz到两千Hz的输出
        ser = serial.Serial('COM4', 2000000, timeout=1)
        print("========= 成功连接 COM4 =========")
        while True:
            # 当波特率和发送频率极高时，每次循环应尽可能吸干缓冲区，并且避免海量的 print 拖慢线程
            while ser.in_waiting > 0:
                data = ser.readline().decode('utf-8', errors='ignore').strip()
                if data:
                    latest_serial_data = data
            time.sleep(0.001)
    except Exception as e:
        print(f"串口COM4读取失败: {e}")

class CustomLogger:
    """ 包含串口数据在内的综合日志记录机制 """
    def __init__(self, controller, ati_sensor):
        self.controller = controller
        self.ati = ati_sensor
        self.is_logging = False
        self.recorded_data = []

    def _record_worker(self, record_fps):
        target_dt = 1.0 / record_fps
        start_time = time.perf_counter()
        
        while self.is_logging:
            loop_start = time.perf_counter()
            try:
                t = loop_start - start_time
                force = self.ati.get_force()
                pos = self.controller.position(verbose=False)
                global latest_serial_data
                row = [t] + list(force) + pos + [latest_serial_data]
                self.recorded_data.append(row)
            except Exception as e:
                print(f"记录异常: {e}")
                
            elapsed = time.perf_counter() - loop_start
            sleep_time = target_dt - elapsed
            if sleep_time > 0:
                time.sleep(sleep_time)

    def start(self, record_fps=2000):
        self.recorded_data = []
        self.is_logging = True
        self.thread = threading.Thread(target=self._record_worker, args=(record_fps,), daemon=True)
        self.thread.start()
        print(f"[Logger] 开始后台同步记录(含串口)，记录频率为主循环最高速率左右")

    def stop_and_save(self, filename="process_data.csv"):
        self.is_logging = False
        if hasattr(self, 'thread'):
            self.thread.join()
        print(f"[Logger] 停止记录，正在保存 {len(self.recorded_data)} 行数据...")
        with open(filename, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(['Time(s)', 'Fx', 'Fy', 'Fz', 'Tx', 'Ty', 'Tz', 'PosX', 'PosY', 'PosZ', 'SerialData'])
            writer.writerows(self.recorded_data)
        print(f"[Logger] 数据已成功保存至 {filename}")

class ControlPanel(QtWidgets.QWidget):
    def __init__(self, controller, sati, logger):
        super().__init__()
        self.controller = controller
        self.ati = sati
        self.logger = logger
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle("硬件控制台")
        self.resize(300, 150)
        layout = QtWidgets.QVBoxLayout()

        # Coordinate inputs
        coord_layout = QtWidgets.QHBoxLayout()
        
        self.input_x = QtWidgets.QDoubleSpinBox()
        self.input_x.setRange(0, 1000)
        self.input_x.setPrefix("X: ")
        self.input_x.setSuffix(" mm")
        self.input_x.setSingleStep(0.5)
        
        self.input_y = QtWidgets.QDoubleSpinBox()
        self.input_y.setRange(0, 1000)
        self.input_y.setPrefix("Y: ")
        self.input_y.setSuffix(" mm")
        self.input_y.setSingleStep(0.5)
        
        self.input_z = QtWidgets.QDoubleSpinBox()
        self.input_z.setRange(0, 1000)
        self.input_z.setPrefix("Z: ")
        self.input_z.setSuffix(" mm")
        self.input_z.setSingleStep(0.5)
        
        coord_layout.addWidget(self.input_x)
        coord_layout.addWidget(self.input_y)
        coord_layout.addWidget(self.input_z)
        layout.addLayout(coord_layout)

        # File name input
        file_layout = QtWidgets.QHBoxLayout()
        file_layout.addWidget(QtWidgets.QLabel("文件名:"))
        self.input_filename = QtWidgets.QLineEdit("process_data.csv")
        file_layout.addWidget(self.input_filename)
        layout.addLayout(file_layout)

        # Move Button
        self.btn_move = QtWidgets.QPushButton("移动位置 (Move)")
        self.btn_move.clicked.connect(self.on_move)
        layout.addWidget(self.btn_move)

        # Record Buttons
        record_layout = QtWidgets.QHBoxLayout()
        self.btn_start = QtWidgets.QPushButton("开始记录数据")
        self.btn_start.clicked.connect(self.on_start_record)
        
        self.btn_stop = QtWidgets.QPushButton("停止并保存")
        self.btn_stop.clicked.connect(self.on_stop_record)
        self.btn_stop.setEnabled(False)
        
        record_layout.addWidget(self.btn_start)
        record_layout.addWidget(self.btn_stop)
        layout.addLayout(record_layout)

        # Auto Experiment Button
        self.btn_auto = QtWidgets.QPushButton("自动扫描实验 (Auto Scan)")
        self.btn_auto.setStyleSheet("background-color: lightblue; font-weight: bold;")
        self.btn_auto.clicked.connect(self.on_auto_experiment)
        layout.addWidget(self.btn_auto)

        # Auto Speed Exp Button
        self.btn_auto_speed = QtWidgets.QPushButton("自动速度实验 (Speed Exp)")
        self.btn_auto_speed.setStyleSheet("background-color: lightgreen; font-weight: bold;")
        self.btn_auto_speed.clicked.connect(self.on_auto_speed_experiment)
        layout.addWidget(self.btn_auto_speed)

        # Auto Tangential Exp Button
        self.btn_auto_tangential = QtWidgets.QPushButton("自动切向实验 (Tangential)")
        self.btn_auto_tangential.setStyleSheet("background-color: lightyellow; font-weight: bold;")
        self.btn_auto_tangential.clicked.connect(self.on_auto_tangential_experiment)
        layout.addWidget(self.btn_auto_tangential)

        self.setLayout(layout)
        
        # Initialize positions
        try:
            pos = self.controller.position(verbose=False)
            self.input_x.setValue(pos[0])
            self.input_y.setValue(pos[1])
            self.input_z.setValue(pos[2])
        except Exception:
            pass

    def on_move(self):
        x = self.input_x.value()
        y = self.input_y.value()
        z = self.input_z.value()
        print(f"指令下发：移动到 X={x}, Y={y}, Z={z}")
        
        # 运动阻塞较长，利用子线程执行
        def move_task():
            try:
                self.btn_move.setEnabled(False)
                self.controller.move(x, y, z)
                print("移动完成.")
            except Exception as e:
                print(f"移动遇到错误: {e}")
            finally:
                self.btn_move.setEnabled(True)
                
        threading.Thread(target=move_task, daemon=True).start()

    def on_start_record(self):
        self.logger.start()
        self.btn_start.setEnabled(False)
        self.btn_stop.setEnabled(True)

    def on_stop_record(self):
        filename = self.input_filename.text().strip()
        if not filename:
            filename = "process_data.csv"
        if not filename.endswith(".csv"):
            filename += ".csv"
            
        self.logger.stop_and_save(filename)
        self.btn_start.setEnabled(True)
        self.btn_stop.setEnabled(False)

    def on_auto_experiment(self):
        """ 自动化网格扫描实验 """
        def auto_task():
            try:
                self.btn_auto.setEnabled(False)
                self.btn_move.setEnabled(False)
                self.btn_start.setEnabled(False)
                self.btn_stop.setEnabled(False)
                print("========= 自动扫描实验开始 =========")
                
                # 网格扫描范围
                x_range = range(211, 222) # 211 到 221
                z_range = range(78, 89) # 78 到 88
                
                for x in x_range:
                    for z in z_range:
                        print(f"\n---> 开始扫描点 X={x}, Z={z}")
                        y = 189.0
                        
                        # 1. 移到初始位置: (x, 189, z)
                        print(f"[{x},{z}] 回到初始深度 Y=189 ...")
                        self.controller.move(x, y, z)
                        time.sleep(1.0) # 给一点稳定时间
                        
                        # 2. 开始记录数据
                        filename = f"scan_X{x}_Z{z}.csv"
                        print(f"[{x},{z}] 开始记录数据: {filename}")
                        self.logger.start()
                        
                        # 3. 接触面探测（寻找 Fz > 0.1N）
                        contact_y = None
                        print(f"[{x},{z}] 正在主动向下探测接触面...")
                        while y < 210.0: # 安全极限深度防撞
                            fz = self.ati.get_force()[2] # 第三个元素对应 Fz
                            if abs(fz) > 0.1:
                                contact_y = y
                                print(f"[{x},{z}] => 接触成功! 测定 |Fz|={abs(fz):.3f}N, 接触深度为 Y={contact_y:.1f}")
                                break
                            
                            y += 0.5
                            self.controller.move(x, y, z)
                            time.sleep(1.0) # 停顿等待走完以及应力稳定
                            
                        # 4. 若找到接触点，则继续往下压 5mm
                        if contact_y is not None:
                            target_y = contact_y + 5.0
                            print(f"[{x},{z}] 开始从接触面向下按压 5mm, 目标深度: Y={target_y:.1f}")
                            while y < target_y:
                                y += 0.5
                                self.controller.move(x, y, z)
                                time.sleep(1.0)
                        else:
                            print(f"[{x},{z}] 警告: 下探过深(>210)仍未找到接触响应，取消本点按压！")
                            
                        # 4.5 Y 轴抬升至 189
                        print(f"[{x},{z}] 抬起复位归中 ...")
                        while y > 189.0:
                            y -= 0.5
                            self.controller.move(x, y, z)
                            time.sleep(1.0)
                            
                        # 5. 停止并保存
                        self.logger.stop_and_save(filename)
                        time.sleep(0.5)
                        
                print("========= 自动扫描实验全部完成 =========")
            except Exception as e:
                print(f"自动实验过程发生错误: {e}")
            finally:
                self.btn_auto.setEnabled(True)
                self.btn_move.setEnabled(True)
                self.btn_start.setEnabled(True)
        
        threading.Thread(target=auto_task, daemon=True).start()

    def on_auto_speed_experiment(self):
        """ 速度实验：对网格上的每个点，以不同速度一压一抬 """
        def speed_task():
            try:
                self.btn_auto_speed.setEnabled(False)
                self.btn_move.setEnabled(False)
                print("========= 自动扫描速度实验开始 =========")
                
                # 网格扫描范围换成 5 个点: 中心1个，四周4个
                points = [
                    (216, 83), # 中心
                    (211, 78), # 左下
                    (221, 78), # 右下
                    (211, 88), # 左上
                    (221, 88)  # 右上
                ]
                
                # 测试不同的下压/抬起速度组合 (mm/s)
                test_speeds = [1.0, 2.0, 5.0, 10.0, 20.0]
                
                for x, z in points:
                    print(f"\n---> 开始速度扫描点 X={x}, Z={z}")
                    
                    # 0. 先探测该点的接触面 (慢慢下压直至 |Fz| > 0.1)
                    print(f"[{x},{z}] 准备探测接触面 Y=189 ...")
                    y = 189.0
                    self.controller.move(x, y, z, vel=20.0)
                    time.sleep(1.0)
                    
                    contact_y = None
                    while y < 210.0:
                        fz = self.ati.get_force()[2]
                        if abs(fz) > 0.1:
                            contact_y = y
                            print(f"[{x},{z}] => 接触成功! 测定 |Fz|={abs(fz):.3f}N, 接触深度为 Y={contact_y:.1f}")
                            break
                        y += 0.5
                        self.controller.move(x, y, z)
                        time.sleep(0.5)

                    if contact_y is None:
                        print(f"[{x},{z}] 警告: 下探过深(>210)仍未找到接触面，跳过该点！")
                        # 归位
                        self.controller.move(x, 189.0, z, vel=20.0)
                        continue
                        
                    target_y = contact_y + 5.0
                    print(f"[{x},{z}] 探知目标下压深度: target_y={target_y:.1f}")
                    
                    # 抬起回安全平面，再打不同速度
                    self.controller.move(x, 189.0, z, vel=20.0)
                    time.sleep(1.0)
                    
                    for vel in test_speeds:
                        print(f"      正在以速度 V={vel} mm/s 进行按压测试...")
                        
                        # 1. 恢复到安全平面准备
                        self.controller.move(x, 189.0, z, vel=20.0)
                        time.sleep(0.5)
                        
                        filename = f"speed_X{x}_Z{z}_V{vel}.csv"
                        self.logger.start()
                        
                        # 2. 直接以目标速度一压到底
                        self.controller.move(x, target_y, z, vel=vel)
                        
                        # 3. 接着以相同的速度弹回
                        self.controller.move(x, 189.0, z, vel=vel)
                        
                        self.logger.stop_and_save(filename)
                        time.sleep(0.5)
                    
                print("========= 自动扫描速度实验全部完成 =========")
            except Exception as e:
                print(f"自动扫描速度实验错误: {e}")
            finally:
                self.btn_auto_speed.setEnabled(True)
                self.btn_move.setEnabled(True)

        threading.Thread(target=speed_task, daemon=True).start()

    def on_auto_tangential_experiment(self):
        """ 切向扫描实验：下压一半深度，然后保持深度横扫 Z 轴，并以不同速度来回滑扫 """
        def tangential_task():
            try:
                self.btn_auto_tangential.setEnabled(False)
                self.btn_move.setEnabled(False)
                print("========= 自动切向移动实验开始 =========")
                
                x = 216.0
                z_start = 78.0
                z_end = 88.0
                y_half = 191.5 # 189 到 194 的中点
                test_speeds = [1.0, 2.0, 5.0, 10.0, 20.0]
                
                for vel in test_speeds:
                    print(f"\n---> 开始以速度 V={vel} mm/s 进行切向来回滑扫测试")
                    
                    # 1. 挪到 Z 的起点上方的安全位置
                    self.controller.move(x, 189.0, z_start, vel=20.0)
                    time.sleep(1.0)
                    
                    # 2. 下压到中心 1/2 深度
                    print(f"下压至 1/2 深度: Y={y_half} ...")
                    self.controller.move(x, y_half, z_start, vel=2.0)
                    time.sleep(1.0)
                    
                    filename = f"tangential_X{x}_Y{y_half}_Z{z_start}to{z_end}_V{vel}.csv"
                    self.logger.start()
                    
                    # 3. 稳住深度，以设定速度沿着 Z 轴正向切扫
                    print(f"开始沿着 Z 轴正向滑扫: {z_start} -> {z_end} ...")
                    self.controller.move(x, y_half, z_end, vel=vel)
                    
                    # 4. 以相同的速度沿着 Z 轴反向回扫
                    print(f"开始沿着 Z 轴反向回扫: {z_end} -> {z_start} ...")
                    self.controller.move(x, y_half, z_start, vel=vel)
                    
                    self.logger.stop_and_save(filename)
                    time.sleep(0.5)
                    
                    # 5. 扫描完后抬起归位
                    print("抬起恢复...")
                    self.controller.move(x, 189.0, z_start, vel=20.0)
                    time.sleep(1.0)
                
                print("========= 自动切向移动实验全部完成 =========")
            except Exception as e:
                print(f"自动切向移动实验错误: {e}")
            finally:
                self.btn_auto_tangential.setEnabled(True)
                self.btn_move.setEnabled(True)

        threading.Thread(target=tangential_task, daemon=True).start()

if __name__ == '__main__':
    # 建立主应用
    app = QtWidgets.QApplication.instance()
    if app is None:
        app = QtWidgets.QApplication(sys.argv)

    # 1. 启动独立线程读取串口数据
    serial_thread = threading.Thread(target=read_serial_data, daemon=True)
    serial_thread.start()

    # 2. 依次初始化传感器和控制器中心
    print("========= 初始化传感器 =========")
    try:
        ati = ATISensor()
    except Exception as e:
        print(f"传感器初始化失败: {e}")
        ati = None

    print("========= 初始化控制器 =========")
    try:
        controller = Controller(ip=b'192.168.0.200', local_ip=b'192.168.0.1')
        controller.setup()
        controller.zero()
    except Exception as e:
        print(f"控制器初始化失败: {e}")
        controller = None

    # 3. 开启控制及监控界面
    if controller and ati:
        logger = CustomLogger(controller, ati)
        panel = ControlPanel(controller, ati, logger)
        panel.show()
        sys.exit(app.exec())
    else:
        print("硬件初始化失败，请检查并重启")
        sys.exit(1)

# 216 189 83
