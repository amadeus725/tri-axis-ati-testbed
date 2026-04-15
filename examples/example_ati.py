from ctypes import *
import ctypes
#import numpy as np
import struct 
import time
import math
import msvcrt
import function

dll = CDLL('C:\DATA\haptic_glove\GAS.dll')
function.Setup(dll)
function.Zero(dll)
import function
import nidaqmx
import atiiaftt
import numpy as np
import cv2
import time
import os
import function
from ctypes import *
import ctypes
import struct 
import math
import msvcrt
import random


task = nidaqmx.Task()
for i in range(6):
    task.ai_channels.add_ai_voltage_chan('Dev1/ai'+str(i))   
DAQ_bias = []
for i in range(10):
    DAQ_bias.append(task.read())
    
ATI_Mini = atiiaftt.FTSensor()
ATI_Mini.createCalibration('FT60628.cal',1)
ATI_Mini.setToolTransform([0,0,45,0,0,0],atiiaftt.FTUnit.DIST_MM,atiiaftt.FTUnit.ANGLE_DEG)
ATI_Mini.bias(np.mean(DAQ_bias,axis=0).tolist())
force_unit_str=atiiaftt.FTUnit.FORCE_N
torque_unit_str=atiiaftt.FTUnit.TORQUE_N_M

def get_force():
    force = np.zeros((5,6))
    for i in range(5):
        force[i,:] = ATI_Mini.convertToFt(task.read())
    return np.mean(force,axis=0)

def generate_random_point():
    a = 12
    b = 8
    center_x = 11
    center_y = 0
    theta = 2 * np.pi * np.random.random()
    r = np.sqrt(np.random.random())
    x = center_x + a * r * np.cos(theta)
    y = center_y + b * r * np.sin(theta)  
    return x, y

def inverse_transform_coordinate(x_new, y_new, z_new):
    y_temp = z_new
    z_temp = -y_new
    x_old = x_new + 41.19
    y_old = y_temp + 226
    z_old = z_temp + 136
    
    return x_old, y_old, z_old


def take_photo(cap, name):
    ret, frame = cap.read()
    save_path = os.path.join('C:/DATA/lvyangdemo/figure', f'{name}.jpg')
    success = cv2.imwrite(save_path, frame)
    time.sleep(0.5)

    


dll = CDLL('C:/DATA/lvyangdemo/GAS.dll')
function.Setup(dll)
function.Zero(dll)
x,y,z = inverse_transform_coordinate(0,0,0)
function.move(dll,x,y,z)#initial position
cap = cv2.VideoCapture(0)

for i in range(1,201,1):
    x,y = generate_random_point()
    #z = random.uniform(0,5)
    for z in range(0,6,1):
        x_new,y_new,z_new = inverse_transform_coordinate(x,y,z)
        if x_new > 61:
            x_new = 61
        function.move(dll,x_new,y_new,z_new)
        time.sleep(0.5)
        name = get_force()
        take_photo(cap, name[2])
cap.release()


    import function
import nidaqmx
import atiiaftt
import matplotlib.pyplot as plt
import numpy as np
import time

# 开启交互模式
plt.ion()

# 初始化数据
x_data = []
y_data = []

# 创建画布和子图
fig, ax = plt.subplots()
line, = ax.plot(x_data, y_data, 'r-') # 'r-' 表示红色的实线

# 设置图表标签
ax.set_title("Real-time Variable Tracking")
ax.set_xlabel("Time (s)")
ax.set_ylabel("Value")

# 模拟实时数据读取循环
try:
    for i in range(10000):
        # 1. 模拟读取一个实时变量
        new_value = function.get_force()
        
        # 2. 更新数据源
        y_data.append(new_value(1))
        
        # 3. 更新线段的数据内容
        line.set_ydata(y_data)
        
        # 4. 动态调整坐标轴范围（确保新数据在视野内）
        ax.relim()
        ax.autoscale_view()
        
        # 5. 刷新画布
        fig.canvas.draw()
        fig.canvas.flush_events()
        
        # 控制更新频率
        time.sleep(0.05)

except KeyboardInterrupt:
    print("Stopped by user")

# 循环结束后保持窗口不关闭
plt.ioff()
plt.show()