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


def safe_nanmax(arr, default=np.nan):
    arr = np.asarray(arr, dtype=float)
    if arr.size == 0 or np.all(np.isnan(arr)):
        return default
    return np.nanmax(arr)


def safe_nanmin(arr, default=np.nan):
    arr = np.asarray(arr, dtype=float)
    if arr.size == 0 or np.all(np.isnan(arr)):
        return default
    return np.nanmin(arr)


def safe_trapz(y, x, default=np.nan):
    y = np.asarray(y, dtype=float)
    x = np.asarray(x, dtype=float)

    mask = np.isfinite(y) & np.isfinite(x)
    if np.sum(mask) < 2:
        return default

    return np.trapz(y[mask], x[mask])

def collect_speed_summary(df, vel):
    time_s = df['Time(s)']
    pos_y = df['PosY']

    # =========================
    # Pressure: 转成相对压强
    # =========================
    n_base = max(5, int(len(df) * 0.1))

    if 'Pressure' in df.columns:
        pressure_baseline = np.nanmedian(df['Pressure'].iloc[:n_base])
        pressure_delta = df['Pressure'] - pressure_baseline
    else:
        pressure_delta = pd.Series(np.full(len(df), np.nan))

    # =========================
    # IMU magnitude
    # =========================
    acc_mag = np.sqrt(
        np.square(df['Acc_X']) +
        np.square(df['Acc_Y']) +
        np.square(df['Acc_Z'])
    )

    gyro_mag = np.sqrt(
        np.square(df['Gyro_X']) +
        np.square(df['Gyro_Y']) +
        np.square(df['Gyro_Z'])
    )

    # =========================
    # RMS helper
    # =========================
    def safe_rms(x):
        x = np.asarray(x, dtype=float)
        if x.size == 0 or np.all(np.isnan(x)):
            return np.nan
        return np.sqrt(np.nanmean(np.square(x)))

    # =========================
    # Pressure-depth hysteresis area
    # 这里用 ∫ ΔP dY 的绝对值作为滞回/路径面积近似
    # =========================
    pressure_depth_area = safe_trapz(pressure_delta, pos_y)
    pressure_depth_area_abs = np.abs(pressure_depth_area)

    summary_item = {
        "Velocity": vel,

        # =========================
        # Force 只作为参考输入，不再作为核心指标
        # =========================
        "Peak_abs_Fz_ref": safe_nanmax(np.abs(df['Fz'])),

        # =========================
        # Pressure 指标
        # =========================
        "Peak_delta_pressure": safe_nanmax(np.abs(pressure_delta)),
        "Pressure_RMS": safe_rms(pressure_delta),
        "Pressure_area_time": safe_trapz(np.abs(pressure_delta), time_s),
        "Pressure_depth_area": pressure_depth_area_abs,

        # =========================
        # Acceleration 指标
        # =========================
        "Peak_AccMag": safe_nanmax(acc_mag),
        "AccMag_RMS": safe_rms(acc_mag),
        "Peak_abs_AccX": safe_nanmax(np.abs(df['Acc_X'])),
        "Peak_abs_AccY": safe_nanmax(np.abs(df['Acc_Y'])),
        "Peak_abs_AccZ": safe_nanmax(np.abs(df['Acc_Z'])),

        # =========================
        # Gyro 指标
        # =========================
        "Peak_GyroMag": safe_nanmax(gyro_mag),
        "GyroMag_RMS": safe_rms(gyro_mag),
        "Peak_abs_GyroX": safe_nanmax(np.abs(df['Gyro_X'])),
        "Peak_abs_GyroY": safe_nanmax(np.abs(df['Gyro_Y'])),
        "Peak_abs_GyroZ": safe_nanmax(np.abs(df['Gyro_Z'])),

        # =========================
        # Depth 参考
        # =========================
        "Max_Depth_Y": safe_nanmax(pos_y),
        "Min_Depth_Y": safe_nanmin(pos_y),
        "Depth_Range_Y": safe_nanmax(pos_y) - safe_nanmin(pos_y),
    }

    return summary_item
def plot_speed_summary(summary, data_dir, target_x, target_z, save_fig=False):
    if not summary:
        print("没有可用于速度对比的 summary 数据。")
        return

    summary_df = pd.DataFrame(summary)
    summary_df = summary_df.sort_values("Velocity")

    # 如果同一速度有重复实验，则自动计算 mean/std/count
    grouped = summary_df.groupby("Velocity").agg(['mean', 'std', 'count'])
    velocities = grouped.index.values

    def get_mean_std(metric):
        mean = grouped[(metric, 'mean')].values
        std = grouped[(metric, 'std')].values
        count = grouped[(metric, 'count')].values
        std = np.nan_to_num(std, nan=0.0)
        return mean, std, count

    fig, axes = plt.subplots(
        2, 3,
        figsize=(16, 8),
        constrained_layout=True
    )

    fig.canvas.manager.set_window_title(
        f"Pressure & IMU Speed Comparison X={target_x}, Z={target_z}"
    )
    fig.suptitle(
        f"Pressure & IMU Speed Comparison  X={target_x}, Z={target_z}"
    )

    # ==========================================================
    # 1. Peak ΔPressure
    # ==========================================================
    ax = axes[0, 0]

    mean, std, count = get_mean_std("Peak_delta_pressure")
    ax.errorbar(
        velocities,
        mean,
        yerr=std,
        marker='o',
        capsize=4,
        linewidth=1.8,
        color='orange'
    )

    ax.set_title("Peak ΔPressure vs Velocity")
    ax.set_xlabel("Velocity")
    ax.set_ylabel("Peak |ΔPressure|")
    ax.grid(True, alpha=0.4)

    # ==========================================================
    # 2. Pressure RMS and Area
    # ==========================================================
    ax = axes[0, 1]

    mean_rms, std_rms, _ = get_mean_std("Pressure_RMS")
    line1 = ax.errorbar(
        velocities,
        mean_rms,
        yerr=std_rms,
        marker='o',
        capsize=4,
        linewidth=1.8,
        color='tab:orange',
        label="Pressure RMS"
    )

    ax.set_title("Pressure RMS / Area vs Velocity")
    ax.set_xlabel("Velocity")
    ax.set_ylabel("Pressure RMS")
    ax.grid(True, alpha=0.4)

    ax2 = ax.twinx()
    mean_area, std_area, _ = get_mean_std("Pressure_area_time")
    line2 = ax2.errorbar(
        velocities,
        mean_area,
        yerr=std_area,
        marker='s',
        capsize=4,
        linewidth=1.8,
        color='tab:red',
        label="∫|ΔP|dt"
    )
    ax2.set_ylabel("Pressure Area")

    lines = [line1, line2]
    labels = [l.get_label() for l in lines]
    ax.legend(lines, labels, loc='best')

    # ==========================================================
    # 3. Pressure-Depth Hysteresis Area
    # ==========================================================
    ax = axes[0, 2]

    mean, std, count = get_mean_std("Pressure_depth_area")
    ax.errorbar(
        velocities,
        mean,
        yerr=std,
        marker='o',
        capsize=4,
        linewidth=1.8,
        color='brown'
    )

    ax.set_title("Pressure-Depth Hysteresis Area")
    ax.set_xlabel("Velocity")
    ax.set_ylabel("|∫ ΔP dY|")
    ax.grid(True, alpha=0.4)

    # ==========================================================
    # 4. Acc Magnitude
    # ==========================================================
    ax = axes[1, 0]

    mean_peak, std_peak, _ = get_mean_std("Peak_AccMag")
    line1 = ax.errorbar(
        velocities,
        mean_peak,
        yerr=std_peak,
        marker='o',
        capsize=4,
        linewidth=1.8,
        color='blue',
        label="Peak |Acc|"
    )

    mean_rms, std_rms, _ = get_mean_std("AccMag_RMS")
    line2 = ax.errorbar(
        velocities,
        mean_rms,
        yerr=std_rms,
        marker='s',
        capsize=4,
        linewidth=1.8,
        color='cyan',
        label="Acc RMS"
    )

    ax.set_title("Acceleration Response vs Velocity")
    ax.set_xlabel("Velocity")
    ax.set_ylabel("Acceleration Magnitude")
    ax.grid(True, alpha=0.4)
    ax.legend()

    # ==========================================================
    # 5. Gyro Magnitude
    # ==========================================================
    ax = axes[1, 1]

    mean_peak, std_peak, _ = get_mean_std("Peak_GyroMag")
    line1 = ax.errorbar(
        velocities,
        mean_peak,
        yerr=std_peak,
        marker='o',
        capsize=4,
        linewidth=1.8,
        color='purple',
        label="Peak |Gyro|"
    )

    mean_rms, std_rms, _ = get_mean_std("GyroMag_RMS")
    line2 = ax.errorbar(
        velocities,
        mean_rms,
        yerr=std_rms,
        marker='s',
        capsize=4,
        linewidth=1.8,
        color='magenta',
        label="Gyro RMS"
    )

    ax.set_title("Gyroscope Response vs Velocity")
    ax.set_xlabel("Velocity")
    ax.set_ylabel("Gyro Magnitude")
    ax.grid(True, alpha=0.4)
    ax.legend()

    # ==========================================================
    # 6. Reference: Peak Fz and Depth Range
    # ==========================================================
    ax = axes[1, 2]

    mean_fz, std_fz, _ = get_mean_std("Peak_abs_Fz_ref")
    line1 = ax.errorbar(
        velocities,
        mean_fz,
        yerr=std_fz,
        marker='o',
        capsize=4,
        linewidth=1.8,
        color='black',
        label="Peak |Fz| ref"
    )

    ax.set_title("Reference Load / Depth")
    ax.set_xlabel("Velocity")
    ax.set_ylabel("Peak |Fz| Reference")
    ax.grid(True, alpha=0.4)

    ax2 = ax.twinx()
    mean_d, std_d, _ = get_mean_std("Depth_Range_Y")
    line2 = ax2.errorbar(
        velocities,
        mean_d,
        yerr=std_d,
        marker='s',
        capsize=4,
        linewidth=1.8,
        color='gray',
        label="Depth Range Y"
    )
    ax2.set_ylabel("Depth Range Y")

    lines = [line1, line2]
    labels = [l.get_label() for l in lines]
    ax.legend(lines, labels, loc='best')

    if save_fig:
        out = os.path.join(
            data_dir,
            f"pressure_imu_speed_summary_X{target_x}_Z{target_z}.png"
        )
        fig.savefig(out, dpi=220)
        print(f"已保存气压与 IMU 速度对比图: {out}")

    print("\n========== Pressure & IMU Speed Summary ==========")
    print(summary_df.to_string(index=False))

def plot_speed_experiment(data_dir, target_x=216, target_z=83, rows_per_page=3, save_fig=False):
    file_pattern = os.path.join(data_dir, f"speed_X{target_x}*_Z{target_z}*_V*.csv")
    files = glob.glob(file_pattern)

    if not files:
        print(f"在 {data_dir} 下未找到坐标 X={target_x}, Z={target_z} 的速度数据文件！")
        return

    files = sorted(files, key=extract_vel)
    num_files = len(files)

    # 分页
    num_pages = int(np.ceil(num_files / rows_per_page))

    # 收集速度对比指标
    summary = []

    for page in range(num_pages):
        page_files = files[page * rows_per_page:(page + 1) * rows_per_page]
        nrows = len(page_files)

        # =================== 图 1：力与气压 ===================
        fig1, axes1 = plt.subplots(
            nrows, 4,
            figsize=(18, 3.2 * nrows),
            squeeze=False,
            constrained_layout=True
        )
        fig1.canvas.manager.set_window_title(
            f"Speed Task Dynamics Page {page + 1}/{num_pages} "
            f"(X={target_x}, Z={target_z})"
        )
        fig1.suptitle(
            f"Speed Task Dynamics Page {page + 1}/{num_pages} "
            f"(X={target_x}, Z={target_z})"
        )

        # =================== 图 2：IMU ===================
        fig2, axes2 = plt.subplots(
            nrows, 3,
            figsize=(15, 3.2 * nrows),
            squeeze=False,
            constrained_layout=True
        )
        fig2.canvas.manager.set_window_title(
            f"Speed Task IMU Page {page + 1}/{num_pages} "
            f"(X={target_x}, Z={target_z})"
        )
        fig2.suptitle(
            f"Speed Task IMU Page {page + 1}/{num_pages} "
            f"(X={target_x}, Z={target_z})"
        )

        for idx, file in enumerate(page_files):
            vel = extract_vel(file)

            try:
                df = pd.read_csv(file)
                if df.empty:
                    continue

                df = extract_serial_data(df)

                required_cols = ['Time(s)', 'PosY', 'Fx', 'Fy', 'Fz']
                missing_cols = [c for c in required_cols if c not in df.columns]
                if missing_cols:
                    print(f"文件缺少必要列 {missing_cols}: {file}")
                    continue

                time_s = df['Time(s)']
                pos_y = df['PosY']

                # 收集 summary
                summary.append(collect_speed_summary(df, vel))

                # 为动态图也使用相对压强显示，更便于观察
                n_base = max(5, int(len(df) * 0.1))
                pressure_baseline = np.nanmedian(df['Pressure'].iloc[:n_base])
                pressure_delta = df['Pressure'] - pressure_baseline

                # =================== 图 1：力与气压 ===================

                # 1.1 力 vs 时间
                ax = axes1[idx, 0]
                ax.plot(time_s, df['Fx'], label='Fx', linewidth=1.5)
                ax.plot(time_s, df['Fy'], label='Fy', linewidth=1.5)
                ax.plot(time_s, df['Fz'], label='Fz', color='red', alpha=0.9, linewidth=1.5)
                ax.set_title("Force vs Time")
                ax.set_ylabel(f"V={vel}\nForce (N)")
                ax.grid(True, alpha=0.4)
                if idx == 0:
                    ax.legend(loc='best')

                # 1.2 力 vs 深度
                ax = axes1[idx, 1]
                ax.plot(pos_y, df['Fx'], label='Fx', linewidth=1.5)
                ax.plot(pos_y, df['Fy'], label='Fy', linewidth=1.5)
                ax.plot(pos_y, df['Fz'], label='Fz', color='red', alpha=0.9, linewidth=1.5)
                ax.set_title("Force vs Depth Y")
                ax.grid(True, alpha=0.4)
                if idx == 0:
                    ax.legend(loc='best')

                # 1.3 位移 + 相对气压 vs 时间
                ax = axes1[idx, 2]
                ax.plot(time_s, pos_y, label='PosY', color='purple', linestyle='--', linewidth=1.5)
                ax_p = ax.twinx()
                ax_p.plot(time_s, pressure_delta, label='ΔPressure', color='orange', linewidth=1.5)

                ax.set_title("Depth & ΔPressure vs Time")
                ax.set_ylabel("PosY (mm)")
                ax_p.set_ylabel("ΔPressure")
                ax.grid(True, alpha=0.4)

                if idx == 0:
                    ax.legend(loc='upper left')
                    ax_p.legend(loc='upper right')

                # 1.4 相对气压 vs 深度
                ax = axes1[idx, 3]
                sc = ax.scatter(
                    pos_y,
                    pressure_delta,
                    c=time_s,
                    cmap='jet',
                    alpha=0.65,
                    s=12
                )
                ax.set_title("ΔPressure vs Depth Y")
                ax.set_ylabel("ΔPressure")
                ax.grid(True, alpha=0.4)

                # 只在第一页第一行加 colorbar，避免太挤
                if page == 0 and idx == 0:
                    cbar = fig1.colorbar(sc, ax=ax, shrink=0.85)
                    cbar.set_label("Time (s)")

                # =================== 图 2：IMU ===================

                # 2.1 Acc X/Y
                ax = axes2[idx, 0]
                ax.plot(time_s, df['Acc_X'], label='Acc_X', color='blue', alpha=0.8, linewidth=1.5)
                ax.plot(time_s, df['Acc_Y'], label='Acc_Y', color='green', alpha=0.8, linewidth=1.5)
                ax.set_title("Acc X/Y vs Time")
                ax.set_ylabel(f"V={vel}\nAcc (g)")
                ax.grid(True, alpha=0.4)
                if idx == 0:
                    ax.legend(loc='best')

                # 2.2 Acc Z
                ax = axes2[idx, 1]
                ax.plot(time_s, df['Acc_Z'], label='Acc_Z', color='red', alpha=0.8, linewidth=1.5)
                ax.set_title("Acc Z vs Time")
                ax.set_ylabel("Acc Z (g)")
                ax.grid(True, alpha=0.4)
                if idx == 0:
                    ax.legend(loc='best')

                # 2.3 Gyro
                ax = axes2[idx, 2]
                ax.plot(time_s, df['Gyro_X'], label='Gyro_X', alpha=0.8, linewidth=1.5)
                ax.plot(time_s, df['Gyro_Y'], label='Gyro_Y', alpha=0.8, linewidth=1.5)
                ax.plot(time_s, df['Gyro_Z'], label='Gyro_Z', alpha=0.8, linewidth=1.5)
                ax.set_title("Gyro vs Time")
                ax.set_ylabel("Gyro (deg/s)")
                ax.grid(True, alpha=0.4)
                if idx == 0:
                    ax.legend(loc='best')

            except Exception as e:
                print(f"读取或画图异常 {file}: {e}")

        # 只给最后一行加 xlabel，减少拥挤
        for i in range(4):
            axes1[-1, i].set_xlabel("Time (s)" if i in [0, 2] else "Depth PosY (mm)")

        for i in range(3):
            axes2[-1, i].set_xlabel("Time (s)")

        if save_fig:
            out1 = os.path.join(
                data_dir,
                f"speed_dynamics_X{target_x}_Z{target_z}_page{page + 1}.png"
            )
            out2 = os.path.join(
                data_dir,
                f"speed_imu_X{target_x}_Z{target_z}_page{page + 1}.png"
            )

            fig1.savefig(out1, dpi=200)
            fig2.savefig(out2, dpi=200)

            print(f"已保存: {out1}")
            print(f"已保存: {out2}")

    # 速度对比图
    plot_speed_summary(summary, data_dir, target_x, target_z, save_fig)

    plt.show()


if __name__ == "__main__":
    data_folder = os.path.abspath(
        os.path.join(os.path.dirname(__file__), "../data/speed_2026_5_18")
    )

    print("生成垂直速度下压实验（动态响应 + 速度对比）图表...")
    plot_speed_experiment(
        data_folder,
        target_x=216,
        target_z=83,
        rows_per_page=3,
        save_fig=False
    )
