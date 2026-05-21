import os
import glob
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

plt.rcParams.update({
    "font.size": 8,
    "axes.titlesize": 9,
    "axes.labelsize": 8,
    "xtick.labelsize": 7,
    "ytick.labelsize": 7,
    "legend.fontsize": 7,
    "figure.titlesize": 11,
})

def extract_serial_data(df):
    acc_x, acc_y, acc_z = [], [], []
    gyro_x, gyro_y, gyro_z = [], [], []
    pres = []
    
    if 'SerialData' not in df.columns:
        return df

    for s in df['SerialData']:
        if isinstance(s, str):
            parts = s.strip('"').split(',')
            if len(parts) >= 8:
                try:
                    acc_x.append(float(parts[0]))
                    acc_y.append(float(parts[1]))
                    acc_z.append(float(parts[2]))
                    gyro_x.append(float(parts[3]))
                    gyro_y.append(float(parts[4]))
                    gyro_z.append(float(parts[5]))
                    pres.append(float(parts[-2]))
                    continue
                except:
                    pass
        acc_x.append(np.nan)
        acc_y.append(np.nan)
        acc_z.append(np.nan)
        gyro_x.append(np.nan)
        gyro_y.append(np.nan)
        gyro_z.append(np.nan)
        pres.append(np.nan)
    
    df['Acc_X'] = acc_x
    df['Acc_Y'] = acc_y
    df['Acc_Z'] = acc_z
    df['Gyro_X'] = gyro_x
    df['Gyro_Y'] = gyro_y
    df['Gyro_Z'] = gyro_z
    df['Pressure'] = pres
    return df

def extract_vel(f):
    try:
        basename = os.path.basename(f)
        v_part = basename.split('_V')[1].replace('.csv', '')
        return float(v_part)
    except:
        return 999.0

def plot_tangential_all_speeds(data_dir):
    file_pattern = os.path.join(data_dir, "tangential_*.csv")
    files = glob.glob(file_pattern)
    
    if not files:
        print(f"在 {data_dir} 下未找到数据文件！")
        return

    files = sorted(files, key=extract_vel)
    num_files = len(files)

    # 三张主图：保持你之前 speed 那种“每个速度一行”的排版
    fig1, axes1 = plt.subplots(num_files, 4, figsize=(24, 3 * num_files), squeeze=False, constrained_layout=True)
    fig1.canvas.manager.set_window_title("Forces & Pressure Dynamics")

    fig2, axes2 = plt.subplots(num_files, 4, figsize=(24, 3 * num_files), squeeze=False, constrained_layout=True)
    fig2.canvas.manager.set_window_title("IMU Acceleration Dynamics")

    fig3, axes3 = plt.subplots(num_files, 2, figsize=(12, 3 * num_files), squeeze=False, constrained_layout=True)
    fig3.canvas.manager.set_window_title("IMU Gyroscope Dynamics")

    # 收集对比图数据
    summary = []

    for idx, file in enumerate(files):
        vel = extract_vel(file)
        try:
            df = pd.read_csv(file)
            if df.empty:
                continue

            df = extract_serial_data(df)

            time_s = df['Time(s)']
            pos_z = df['PosZ']
            distance = np.abs(df['PosZ'].diff()).fillna(0).cumsum()

            # =================== 图 1：力与气压 ===================
            ax = axes1[idx, 0]
            ax.plot(time_s, df['Fx'], label='Fx')
            ax.plot(time_s, df['Fy'], label='Fy')
            ax.plot(time_s, df['Fz'], label='Fz', color='red', alpha=0.9)
            ax.set_title("Force vs Time")
            ax.set_ylabel(f"V={vel}\nForce (N)")
            ax.grid(True, alpha=0.4)
            if idx == 0:
                ax.legend(loc='best')

            ax = axes1[idx, 1]
            ax.plot(distance, df['Fx'], label='Fx')
            ax.plot(distance, df['Fy'], label='Fy')
            ax.plot(distance, df['Fz'], label='Fz', color='red', alpha=0.9)
            ax.set_title("Force vs Distance")
            ax.grid(True, alpha=0.4)
            if idx == 0:
                ax.legend(loc='best')

            ax = axes1[idx, 2]
            ax.plot(time_s, pos_z, label='PosZ', color='purple', linestyle='--')
            ax_p = ax.twinx()
            ax_p.plot(time_s, df['Pressure'], label='Pressure', color='orange')
            ax.set_title("PosZ & Pressure vs Time")
            ax.set_ylabel("Position Z (mm)")
            ax_p.set_ylabel("Air Pressure")
            ax.grid(True, alpha=0.4)
            if idx == 0:
                ax.legend(loc='upper left')
                ax_p.legend(loc='upper right')

            ax = axes1[idx, 3]
            ax.plot(distance, pos_z, label='PosZ', color='purple', linestyle='--')
            ax_p = ax.twinx()
            ax_p.plot(distance, df['Pressure'], label='Pressure', color='orange')
            ax.set_title("PosZ & Pressure vs Distance")
            ax.grid(True, alpha=0.4)
            if idx == 0:
                ax.legend(loc='upper left')
                ax_p.legend(loc='upper right')

            # =================== 图 2：加速度 ===================
            ax = axes2[idx, 0]
            ax.plot(time_s, df['Acc_X'], label='Acc_X', color='blue', alpha=0.8)
            ax.plot(time_s, df['Acc_Y'], label='Acc_Y', color='green', alpha=0.8)
            ax.set_title("Acc X/Y vs Time")
            ax.set_ylabel(f"V={vel}\nAcc (g)")
            ax.grid(True, alpha=0.4)
            if idx == 0:
                ax.legend(loc='best')

            ax = axes2[idx, 1]
            ax.plot(distance, df['Acc_X'], label='Acc_X', color='blue', alpha=0.8)
            ax.plot(distance, df['Acc_Y'], label='Acc_Y', color='green', alpha=0.8)
            ax.set_title("Acc X/Y vs Distance")
            ax.grid(True, alpha=0.4)
            if idx == 0:
                ax.legend(loc='best')

            ax = axes2[idx, 2]
            ax.plot(time_s, df['Acc_Z'], label='Acc_Z', color='red', alpha=0.8)
            ax.set_title("Acc Z vs Time")
            ax.set_ylabel("Acc Z (g)")
            ax.grid(True, alpha=0.4)
            if idx == 0:
                ax.legend(loc='best')

            ax = axes2[idx, 3]
            ax.plot(distance, df['Acc_Z'], label='Acc_Z', color='red', alpha=0.8)
            ax.set_title("Acc Z vs Distance")
            ax.grid(True, alpha=0.4)
            if idx == 0:
                ax.legend(loc='best')

            # =================== 图 3：角速度 ===================
            ax = axes3[idx, 0]
            ax.plot(time_s, df['Gyro_X'], label='Gyro_X', alpha=0.8)
            ax.plot(time_s, df['Gyro_Y'], label='Gyro_Y', alpha=0.8)
            ax.plot(time_s, df['Gyro_Z'], label='Gyro_Z', alpha=0.8)
            ax.set_title("Gyro vs Time")
            ax.set_ylabel(f"V={vel}\nGyro (deg/s)")
            ax.grid(True, alpha=0.4)
            if idx == 0:
                ax.legend(loc='best')

            ax = axes3[idx, 1]
            ax.plot(distance, df['Gyro_X'], label='Gyro_X', alpha=0.8)
            ax.plot(distance, df['Gyro_Y'], label='Gyro_Y', alpha=0.8)
            ax.plot(distance, df['Gyro_Z'], label='Gyro_Z', alpha=0.8)
            ax.set_title("Gyro vs Distance")
            ax.grid(True, alpha=0.4)
            if idx == 0:
                ax.legend(loc='best')

            # =================== 收集对比指标 ===================
            summary.append({
                "Velocity": vel,
                "Peak_Fx": np.nanmax(np.abs(df['Fx'])),
                "Peak_Fy": np.nanmax(np.abs(df['Fy'])),
                "Peak_Fz": np.nanmax(np.abs(df['Fz'])),
                "Peak_Pressure": np.nanmax(df['Pressure']),
                "Peak_AccZ": np.nanmax(np.abs(df['Acc_Z'])),
                "Peak_GyroMag": np.nanmax(np.sqrt(
                    np.square(df['Gyro_X']) + np.square(df['Gyro_Y']) + np.square(df['Gyro_Z'])
                ))
            })

        except Exception as e:
            print(f"读取或画图异常 {file}: {e}")

    # 最后一行加 x 轴标签
    for i in range(4):
        axes1[-1, i].set_xlabel("Time (s)" if i % 2 == 0 else "Moving Distance (mm)")
        axes2[-1, i].set_xlabel("Time (s)" if i % 2 == 0 else "Moving Distance (mm)")
    for i in range(2):
        axes3[-1, i].set_xlabel("Time (s)" if i == 0 else "Moving Distance (mm)")

    # =================== 图 4：对比图 ===================
    if summary:
        summary_df = pd.DataFrame(summary).sort_values("Velocity")

        fig4, axes4 = plt.subplots(2, 2, figsize=(12, 8), constrained_layout=True)
        fig4.canvas.manager.set_window_title("Tangential Speed Comparison")
        fig4.suptitle("Speed Comparison Summary")

        ax = axes4[0, 0]
        ax.plot(summary_df["Velocity"], summary_df["Peak_Fx"], marker='o', label='Peak |Fx|')
        ax.plot(summary_df["Velocity"], summary_df["Peak_Fy"], marker='o', label='Peak |Fy|')
        ax.plot(summary_df["Velocity"], summary_df["Peak_Fz"], marker='o', label='Peak |Fz|')
        ax.set_title("Peak Force vs Velocity")
        ax.set_xlabel("Velocity")
        ax.set_ylabel("Peak Force (N)")
        ax.grid(True, alpha=0.4)
        ax.legend()

        ax = axes4[0, 1]
        ax.plot(summary_df["Velocity"], summary_df["Peak_Pressure"], marker='o', color='orange')
        ax.set_title("Peak Pressure vs Velocity")
        ax.set_xlabel("Velocity")
        ax.set_ylabel("Peak Pressure")
        ax.grid(True, alpha=0.4)

        ax = axes4[1, 0]
        ax.plot(summary_df["Velocity"], summary_df["Peak_AccZ"], marker='o', color='red')
        ax.set_title("Peak |Acc_Z| vs Velocity")
        ax.set_xlabel("Velocity")
        ax.set_ylabel("Peak |Acc_Z| (g)")
        ax.grid(True, alpha=0.4)

        ax = axes4[1, 1]
        ax.plot(summary_df["Velocity"], summary_df["Peak_GyroMag"], marker='o', color='purple')
        ax.set_title("Peak Gyro Magnitude vs Velocity")
        ax.set_xlabel("Velocity")
        ax.set_ylabel("Peak Gyro (deg/s)")
        ax.grid(True, alpha=0.4)

    plt.show()

if __name__ == "__main__":
    data_folder = os.path.abspath(os.path.join(os.path.dirname(__file__), "../data/tangential_2026_5_18"))
    print("生成切向实验不同速度下的力、气压、IMU对比图...")
    plot_tangential_all_speeds(data_folder)
