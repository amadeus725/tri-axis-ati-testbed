import os
import glob
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D

def analyze_and_plot(data_dirs):
    if isinstance(data_dirs, str):
        data_dirs = [data_dirs]
        
    # 存储所有目录中每个网格点的压力最大值: {(x, z): [max1, max2, ...]}
    point_data = {}

    # 1. 解析所有文件，提取每个网格点的最大下压力 (或气压绝对值的最大值)
    for d in data_dirs:
        file_pattern = os.path.join(d, "scan_X*_Z*.csv")
        files = glob.glob(file_pattern)
        
        if not files:
            print(f"在 {d} 下未找到数据文件！")
            continue

        for file in files:
            # 解析文件名中的 X 和 Z 坐标
            basename = os.path.basename(file) # e.g., scan_X70_Z78.csv
            parts = basename.replace('.csv', '').split('_')
            try:
                x_val = int(parts[1][1:]) # 提取 X 后面的数字
                z_val = int(parts[2][1:]) # 提取 Z 后面的数字
            except Exception as e:
                continue
                
            try:
                # 读取 CSV
                df = pd.read_csv(file)
                if df.empty:
                    continue
                
                # 通常下压受到的反作用力可能为正也可能为负，取绝对值的最大值作为该点的最大受力程度
                def _extract_pressure(s):
                    if isinstance(s, str):
                        parts = s.strip('"').split(',')
                        if len(parts) >= 7:
                            try:
                                # 假设倒数第二个是气压，像 100979
                                return float(parts[-2])
                            except:
                                pass
                    return np.nan

                df['Pressure'] = df['SerialData'].apply(_extract_pressure)

                max_fy = np.max(np.abs(df['Pressure'])) 
                
                if (x_val, z_val) not in point_data:
                    point_data[(x_val, z_val)] = []
                point_data[(x_val, z_val)].append(max_fy)
            except Exception as e:
                print(f"读取异常 {file}: {e}")

    # 对多个实验收集到的同一个坐标下的最大值取平均
    records = []
    for (x, z), vals in point_data.items():
        if vals:
            records.append({
                'X': x,
                'Z': z,
                'Max_Fy': np.mean(vals)
            })

    df_res = pd.DataFrame(records)
    if df_res.empty:
        print("未提取到有效数据。")
        return

    # 2. 将数据透视转化为 2D 网格矩阵，用于画热力图
    # 行为 Z，列为 X，值为最大力
    pivot_table = df_res.pivot_table(index='Z', columns='X', values='Max_Fy')
    
    X_cols = pivot_table.columns.values
    Z_index = pivot_table.index.values

    # === 可视化部分 ===
    fig = plt.figure(figsize=(14, 6))

    # 图 1：2D 热力图
    ax1 = fig.add_subplot(121)
    # 使用 contourf 或者 imshow
    c = ax1.contourf(X_cols, Z_index, pivot_table.values, cmap='viridis', levels=20)
    fig.colorbar(c, ax=ax1, label='Max Pressure (Pa)')
    ax1.set_title('Max Pressure Distribution (X-Z Plane)')
    ax1.set_xlabel('X Position (mm)')
    ax1.set_ylabel('Z Position (mm)')

    # 图 2：3D 曲面图
    ax2 = fig.add_subplot(122, projection='3d')
    X_grid, Z_grid = np.meshgrid(X_cols, Z_index)
    surf = ax2.plot_surface(X_grid, Z_grid, pivot_table.values, cmap='viridis', edgecolor='none')
    fig.colorbar(surf, ax=ax2, shrink=0.5, aspect=0.5, label='Max Pressure (Pa)')
    ax2.set_title('3D Surface of Pressure Response')
    ax2.set_xlabel('X (mm)')
    ax2.set_ylabel('Z (mm)')
    ax2.set_zlabel('Pressure')
    
    plt.tight_layout()
    plt.show()

def analyze_and_plot_fz(data_dirs):
    if isinstance(data_dirs, str):
        data_dirs = [data_dirs]
        
    point_data = {}

    for d in data_dirs:
        file_pattern = os.path.join(d, "scan_X*_Z*.csv")
        files = glob.glob(file_pattern)
        
        if not files:
            continue

        for file in files:
            basename = os.path.basename(file)
            parts = basename.replace('.csv', '').split('_')
            try:
                x_val = int(parts[1][1:])
                z_val = int(parts[2][1:])
            except Exception as e:
                continue
                
            try:
                df = pd.read_csv(file)
                if df.empty or 'Fz' not in df.columns:
                    continue
                
                # 直接取 Fz 列绝对值的最大值作为该点的 ATI 最大受力
                max_fz = np.max(np.abs(df['Fz'])) 
                
                if (x_val, z_val) not in point_data:
                    point_data[(x_val, z_val)] = []
                point_data[(x_val, z_val)].append(max_fz)
            except Exception as e:
                print(f"读取异常 {file}: {e}")

    records = []
    for (x, z), vals in point_data.items():
        if vals:
            records.append({
                'X': x,
                'Z': z,
                'Max_Fz': np.mean(vals)
            })

    df_res = pd.DataFrame(records)
    if df_res.empty:
        print("未提取到有效数据。")
        return

    pivot_table = df_res.pivot_table(index='Z', columns='X', values='Max_Fz')
    
    X_cols = pivot_table.columns.values
    Z_index = pivot_table.index.values

    fig = plt.figure(figsize=(14, 6))

    ax1 = fig.add_subplot(121)
    # 使用 plasma 配色，以便和气压的图做区分
    c = ax1.contourf(X_cols, Z_index, pivot_table.values, cmap='plasma', levels=20)
    fig.colorbar(c, ax=ax1, label='Max Fz (N)')
    ax1.set_title('Max Fz Distribution (X-Z Plane)')
    ax1.set_xlabel('X Position (mm)')
    ax1.set_ylabel('Z Position (mm)')

    ax2 = fig.add_subplot(122, projection='3d')
    X_grid, Z_grid = np.meshgrid(X_cols, Z_index)
    surf = ax2.plot_surface(X_grid, Z_grid, pivot_table.values, cmap='plasma', edgecolor='none')
    fig.colorbar(surf, ax=ax2, shrink=0.5, aspect=0.5, label='Max Fz (N)')
    ax2.set_title('3D Surface of Fz Response')
    ax2.set_xlabel('X (mm)')
    ax2.set_ylabel('Z (mm)')
    ax2.set_zlabel('Force (N)')
    
    plt.tight_layout()
    plt.show()

def plot_pressure_vs_fz(data_dir, points=[(211, 83), (218, 83), (214, 83), (220, 79)]):
    """
    针对几个特定的 (X, Z) 坐标点，绘制 气压值(SerialData) vs Fz 的关系图
    """
    fig, axes = plt.subplots(2, 2, figsize=(12, 10))
    axes = axes.flatten()

    for idx, (x, z) in enumerate(points):
        if idx >= len(axes):
            break
            
        file_path = os.path.join(data_dir, f"scan_X{x}_Z{z}.csv")
        ax = axes[idx]
        
        if not os.path.exists(file_path):
            ax.set_title(f"X={x}, Z={z} (File Not Found)")
            continue
            
        try:
            df = pd.read_csv(file_path)
            if df.empty or 'SerialData' not in df.columns:
                ax.set_title(f"X={x}, Z={z} (No SerialData)")
                continue
                
            # "0.01,0.13,-1.05,-0.01,-0.09,0.03,100979,28.9"
            # 其中含有逗号分隔的数值。气压在倒数第二位(索引为6)。
            def _extract_pressure(s):
                if isinstance(s, str):
                    parts = s.strip('"').split(',')
                    if len(parts) >= 7:
                        try:
                            # 假设倒数第二个是气压，像 100979
                            return float(parts[-2])
                        except:
                            pass
                return np.nan

            df['Pressure'] = df['SerialData'].apply(_extract_pressure)
            
            # 滤除没有气压数据和Fz数据的行
            df_clean = df.dropna(subset=['Pressure', 'Fz'])
            
            if df_clean.empty:
                ax.set_title(f"X={x}, Z={z} (Data invalid)")
                continue

            # 使用散点图绘制 气压 vs Fz (Fz取绝对值以方便看受力幅值，或保留原值)
            # 为了观察过程，我们用颜色深浅代表时间(或Y轴下压位移)
            sc = ax.scatter(df_clean['Pressure'], df_clean['Fz'], c=df_clean['PosY'], cmap='jet', alpha=0.7)
            fig.colorbar(sc, ax=ax, label='Y Position (Depth mm)')
            
            # --- 进行多项式拟合 ---
            try:
                x_data = df_clean['Pressure'].values
                y_data = df_clean['Fz'].values
                valid = np.isfinite(x_data) & np.isfinite(y_data)
                
                if np.sum(valid) > 2:
                    x_v, y_v = x_data[valid], y_data[valid]
                    # 采用一次多项式拟合曲线 (度数为1)
                    coef = np.polyfit(x_v, y_v, 1)
                    fit_fn = np.poly1d(coef)
                    
                    x_fit = np.linspace(x_v.min(), x_v.max(), 100)
                    y_fit = fit_fn(x_fit)
                    
                    ax.plot(x_fit, y_fit, color='black', linewidth=2, linestyle='--', 
                            label=f'Fit: y={coef[0]:.2e}x+{coef[1]:.2f}')
                    ax.legend(loc='best')
            except Exception as fit_err:
                print(f"拟合失败: {fit_err}")
            
            ax.set_title(f"Pressure vs Fz at X={x}, Z={z}")
            ax.set_xlabel('Serial Air Pressure')
            ax.set_ylabel('Fz Force (N)')
            ax.grid(True)
            
        except Exception as e:
            ax.set_title(f"X={x}, Z={z} (Error: {e})")
            
    plt.tight_layout()
    plt.show()
def plot_pressure_delta_vs_fz(
    data_dir,
    points=[(211, 83), (218, 83), (214, 83), (220, 79)],
    fz_threshold=0.1,
    pressure_delta_threshold=100,
    fit_degree=1
):
    """
    针对几个特定的 (X, Z) 坐标点，绘制 Fz vs 气压增量(ΔPressure) 的关系图。

    改动：
    1. 筛掉 |Fz| <= fz_threshold 的数据点
    2. 筛掉 |ΔPressure| <= pressure_delta_threshold 的死区点
    3. 按下压 / 上回过程分别拟合
    4. x轴改为 Fz，y轴改为 ΔPressure
    """

    fig, axes = plt.subplots(2, 2, figsize=(13, 10))
    axes = axes.flatten()

    for idx, (x, z) in enumerate(points):
        if idx >= len(axes):
            break

        file_path = os.path.join(data_dir, f"scan_X{x}_Z{z}.csv")
        ax = axes[idx]

        if not os.path.exists(file_path):
            ax.set_title(f"X={x}, Z={z} (File Not Found)")
            continue

        try:
            df = pd.read_csv(file_path)

            if df.empty or 'SerialData' not in df.columns or 'Fz' not in df.columns:
                ax.set_title(f"X={x}, Z={z} (Missing SerialData/Fz)")
                continue

            df['Pressure'] = df['SerialData'].apply(_extract_pressure_from_serial)

            required_cols = ['Pressure', 'Fz']
            if 'PosY' in df.columns:
                required_cols.append('PosY')

            df_clean = df.dropna(subset=required_cols).copy()

            if df_clean.empty:
                ax.set_title(f"X={x}, Z={z} (Data invalid)")
                continue

            # baseline
            n_head = min(5, len(df_clean))
            p0 = df_clean['Pressure'].head(n_head).mean()
            df_clean['PressureDelta'] = df_clean['Pressure'] - p0

            df_clean = df_clean.reset_index(drop=True)

            # 分下压 / 上回
            if 'PosY' in df_clean.columns and len(df_clean) >= 3:
                y0 = df_clean['PosY'].head(n_head).mean()
                turn_idx = (df_clean['PosY'] - y0).abs().idxmax()

                df_clean['Phase'] = 'release'
                df_clean.loc[:turn_idx, 'Phase'] = 'press'
                df_clean.loc[turn_idx + 1:, 'Phase'] = 'release'
            else:
                turn_idx = len(df_clean) // 2
                df_clean['Phase'] = 'release'
                df_clean.loc[:turn_idx, 'Phase'] = 'press'
                df_clean.loc[turn_idx + 1:, 'Phase'] = 'release'

            # 同时筛 Fz 和 ΔP
            df_fit = df_clean[
                (np.abs(df_clean['Fz']) > fz_threshold) &
                (np.abs(df_clean['PressureDelta']) > pressure_delta_threshold)
            ].copy()

            if df_fit.empty:
                ax.set_title(
                    f"X={x}, Z={z} (No data after filtering)\n"
                    f"|Fz|>{fz_threshold}, |ΔP|>{pressure_delta_threshold}"
                )
                continue

            df_press = df_fit[df_fit['Phase'] == 'press']
            df_release = df_fit[df_fit['Phase'] == 'release']

            # 散点图：x=Fz, y=ΔPressure
            ax.scatter(
                df_press['Fz'],
                df_press['PressureDelta'],
                color='tab:blue',
                alpha=0.65,
                s=25,
                label=f'Press data, n={len(df_press)}'
            )

            ax.scatter(
                df_release['Fz'],
                df_release['PressureDelta'],
                color='tab:orange',
                alpha=0.65,
                s=25,
                label=f'Release data, n={len(df_release)}'
            )

            # 拟合：ΔPressure = k * Fz + b
            def _fit_and_plot(df_phase, color, name):
                if len(df_phase) <= fit_degree + 1:
                    return

                x_data = df_phase['Fz'].values
                y_data = df_phase['PressureDelta'].values

                valid = np.isfinite(x_data) & np.isfinite(y_data)
                x_v = x_data[valid]
                y_v = y_data[valid]

                if len(x_v) <= fit_degree + 1:
                    return

                coef = np.polyfit(x_v, y_v, fit_degree)
                fit_fn = np.poly1d(coef)

                x_fit = np.linspace(x_v.min(), x_v.max(), 100)
                y_fit = fit_fn(x_fit)

                y_pred = fit_fn(x_v)
                ss_res = np.sum((y_v - y_pred) ** 2)
                ss_tot = np.sum((y_v - np.mean(y_v)) ** 2)
                r2 = 1 - ss_res / ss_tot if ss_tot > 0 else np.nan

                if fit_degree == 1:
                    label = (
                        f'{name} fit: '
                        f'ΔP={coef[0]:.3e}Fz+{coef[1]:.2f}, '
                        f'R²={r2:.3f}'
                    )
                else:
                    label = f'{name} fit, R²={r2:.3f}'

                ax.plot(
                    x_fit,
                    y_fit,
                    color=color,
                    linewidth=2.5,
                    linestyle='--',
                    label=label
                )

            _fit_and_plot(df_press, 'tab:blue', 'Press')
            _fit_and_plot(df_release, 'tab:orange', 'Release')

            ax.axvline(fz_threshold, color='gray', linestyle=':', linewidth=1)
            ax.axvline(-fz_threshold, color='gray', linestyle=':', linewidth=1)

            ax.set_title(
                f"ΔPressure vs Fz at X={x}, Z={z}\n"
                f"P0={p0:.1f}, filter: |Fz|>{fz_threshold}N, |ΔP|>{pressure_delta_threshold}Pa"
            )
            ax.set_xlabel('Fz Force (N)')
            ax.set_ylabel('Δ Air Pressure (Pa)')
            ax.grid(True)
            ax.legend(loc='best', fontsize=8)

        except Exception as e:
            ax.set_title(f"X={x}, Z={z} Error: {e}")

    plt.tight_layout()
    plt.show()

def plot_time_series_comparison(data_dir, points=[(74, 83), (77, 83)]):
    """
    针对几个特定的 (X, Z) 坐标点，绘制 时序上的数据对比图
    """
    for x, z in points:
        file_path = os.path.join(data_dir, f"scan_X{x}_Z{z}.csv")
        if not os.path.exists(file_path):
            print(f"时序图: 找不到文件 {file_path}")
            continue
            
        try:
            df = pd.read_csv(file_path)
            if df.empty:
                continue
                
            def _extract_all_serial(df):
                acc_x, acc_y, acc_z = [], [], []
                gyro_x, gyro_y, gyro_z = [], [], []
                pres = []
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
                
            if 'SerialData' in df.columns:
                _extract_all_serial(df)
            else:
                for col in ['Acc_X', 'Acc_Y', 'Acc_Z', 'Gyro_X', 'Gyro_Y', 'Gyro_Z', 'Pressure']:
                    df[col] = np.nan

            # 数据提取
            time_s = df['Time(s)']
            
            # 使用5个平行的子图，强制X轴对齐
            fig, (ax1, ax2, ax3, ax4, ax5) = plt.subplots(5, 1, figsize=(10, 10), sharex=True)
            
            # 子图1: 高度下压情况 (PosY)
            ax1.plot(time_s, df['PosY'], label='Position Y', color='blue', linewidth=2)
            ax1.set_title(f"Time Series Overview at X={x}, Z={z}")
            ax1.set_ylabel("PosY(mm)")
            ax1.grid(True)
            ax1.legend(loc='upper right')

            # 子图2: 三维力 Fx, Fy, Fz
            ax2.plot(time_s, df['Fx'], label='Fx', alpha=0.8)
            ax2.plot(time_s, df['Fy'], label='Fy', alpha=0.8)
            ax2.plot(time_s, df['Fz'], label='Fz', color='red', alpha=0.9, linewidth=2)
            ax2.set_ylabel("Force(N)")
            ax2.grid(True)
            ax2.legend(loc='upper right')
            
            # 子图3: IMU 加速度
            ax3.plot(time_s, df['Acc_X'], label='Acc_X', alpha=0.8)
            ax3.plot(time_s, df['Acc_Y'], label='Acc_Y', alpha=0.8)
            ax3.plot(time_s, df['Acc_Z'], label='Acc_Z', alpha=0.8)
            ax3.set_ylabel("Acc (g)")
            ax3.grid(True)
            ax3.legend(loc='upper right')
            
            # 子图4: IMU 角速度
            ax4.plot(time_s, df['Gyro_X'], label='Gyro_X', alpha=0.8)
            ax4.plot(time_s, df['Gyro_Y'], label='Gyro_Y', alpha=0.8)
            ax4.plot(time_s, df['Gyro_Z'], label='Gyro_Z', alpha=0.8)
            ax4.set_ylabel("Gyro (deg/s)")
            ax4.grid(True)
            ax4.legend(loc='upper right')

            # 子图5: 气压变化情况
            ax5.plot(time_s, df['Pressure'], label='Pressure', color='orange', linewidth=2)
            ax5.set_ylabel("Pressure")
            ax5.set_xlabel("Time (s)")
            ax5.grid(True)
            ax5.legend(loc='upper right')

            plt.tight_layout()
            plt.show()
            
        except Exception as e:
            print(f"时序图生成出错 X={x}, Z={z}: {e}")

def plot_imu_detail(data_dir, points=[(74, 83), (77, 83)]):
    """
    专门针对特定点，把 IMU 数据拆分成更好的范围单独画图
    """
    for x, z in points:
        file_path = os.path.join(data_dir, f"scan_X{x}_Z{z}.csv")
        if not os.path.exists(file_path):
            continue
            
        try:
            df = pd.read_csv(file_path)
            if df.empty:
                continue
                
            def _extract_all_serial(df):
                acc_x, acc_y, acc_z = [], [], []
                gyro_x, gyro_y, gyro_z = [], [], []
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
                                continue
                            except:
                                pass
                    acc_x.append(np.nan)
                    acc_y.append(np.nan)
                    acc_z.append(np.nan)
                    gyro_x.append(np.nan)
                    gyro_y.append(np.nan)
                    gyro_z.append(np.nan)
                
                df['Acc_X'] = acc_x
                df['Acc_Y'] = acc_y
                df['Acc_Z'] = acc_z
                df['Gyro_X'] = gyro_x
                df['Gyro_Y'] = gyro_y
                df['Gyro_Z'] = gyro_z
                
            if 'SerialData' in df.columns:
                _extract_all_serial(df)
            else:
                continue

            time_s = df['Time(s)']
            
            # 使用3个子图: 1. Acc_X & Acc_Y  2. Acc_Z  3. Gyro 
            fig, (ax1, ax2, ax3) = plt.subplots(3, 1, figsize=(10, 8), sharex=True)
            
            # XY 和 Z 轴差距过大(因为存在重力加速度)，分图绘制
            ax1.plot(time_s, df['Acc_X'], label='Acc_X', color='blue', alpha=0.8)
            ax1.plot(time_s, df['Acc_Y'], label='Acc_Y', color='green', alpha=0.8)
            ax1.set_title(f"IMU Detail at X={x}, Z={z}")
            ax1.set_ylabel("Acc X/Y (g)")
            ax1.grid(True)
            ax1.legend(loc='upper right')

            ax2.plot(time_s, df['Acc_Z'], label='Acc_Z', color='red', alpha=0.8)
            ax2.set_ylabel("Acc Z (g)")
            ax2.grid(True)
            ax2.legend(loc='upper right')

            ax3.plot(time_s, df['Gyro_X'], label='Gyro_X', alpha=0.8)
            ax3.plot(time_s, df['Gyro_Y'], label='Gyro_Y', alpha=0.8)
            ax3.plot(time_s, df['Gyro_Z'], label='Gyro_Z', alpha=0.8)
            ax3.set_ylabel("Gyro (deg/s)")
            ax3.set_xlabel("Time (s)")
            ax3.grid(True)
            ax3.legend(loc='upper right')

            plt.tight_layout()
            plt.show()
            
        except Exception as e:
            print(f"IMU 图生成出错 X={x}, Z={z}: {e}")

def _extract_pressure_from_serial(s):
    if isinstance(s, str):
        parts = s.strip('"').split(',')
        if len(parts) >= 7:
            try:
                return float(parts[-2])
            except:
                pass
    return np.nan

def _fit_press_release_pressure_sensitivity(
    df,
    fz_threshold=0.1,
    pressure_delta_threshold=100,
    fit_degree=1,
    use_abs_mean=True
):
    """
    拟合气压灵敏度：
        ΔPressure = k * Fz + b

    返回：
        sens_press, sens_release, sens_avg, p0

    单位：
        Pa/N
    """
    if df.empty or 'SerialData' not in df.columns or 'Fz' not in df.columns:
        return np.nan, np.nan, np.nan, np.nan

    df = df.copy()
    df['Pressure'] = df['SerialData'].apply(_extract_pressure_from_serial)
    df = df.dropna(subset=['Pressure', 'Fz']).copy()

    if df.empty:
        return np.nan, np.nan, np.nan, np.nan

    # baseline pressure
    n_head = min(5, len(df))
    p0 = df['Pressure'].head(n_head).mean()
    df['PressureDelta'] = df['Pressure'] - p0

    df = df.reset_index(drop=True)

    # 用 PosY 找下压 / 上回分界点
    if 'PosY' in df.columns and len(df) >= 3:
        y0 = df['PosY'].head(n_head).mean()
        turn_idx = (df['PosY'] - y0).abs().idxmax()

        df['Phase'] = 'release'
        df.loc[:turn_idx, 'Phase'] = 'press'
        df.loc[turn_idx + 1:, 'Phase'] = 'release'
    else:
        turn_idx = len(df) // 2
        df['Phase'] = 'release'
        df.loc[:turn_idx, 'Phase'] = 'press'

    # 同时筛 Fz 和 ΔP，去掉死区点
    df_fit = df[
        (np.abs(df['Fz']) > fz_threshold) &
        (np.abs(df['PressureDelta']) > pressure_delta_threshold)
    ].copy()

    if df_fit.empty:
        return np.nan, np.nan, np.nan, p0

    def _one_phase_sensitivity(d):
        if len(d) <= fit_degree + 1:
            return np.nan

        # X 是 Fz，Y 是 PressureDelta
        x = d['Fz'].values
        y = d['PressureDelta'].values

        valid = np.isfinite(x) & np.isfinite(y)
        x = x[valid]
        y = y[valid]

        if len(x) <= fit_degree + 1:
            return np.nan

        coef = np.polyfit(x, y, fit_degree)

        # 一次拟合时 coef[0] 就是 Pa/N
        return coef[0] if fit_degree >= 1 else np.nan

    df_press = df_fit[df_fit['Phase'] == 'press']
    df_release = df_fit[df_fit['Phase'] == 'release']

    sens_press = _one_phase_sensitivity(df_press)
    sens_release = _one_phase_sensitivity(df_release)

    sens_list = []
    if np.isfinite(sens_press):
        sens_list.append(abs(sens_press) if use_abs_mean else sens_press)

    if np.isfinite(sens_release):
        sens_list.append(abs(sens_release) if use_abs_mean else sens_release)

    sens_avg = np.mean(sens_list) if len(sens_list) > 0 else np.nan

    return sens_press, sens_release, sens_avg, p0

def plot_pressure_sensitivity_heatmap(
    data_dirs,
    fz_threshold=0.1,
    pressure_delta_threshold=100,
    fit_degree=1,
    use_abs_mean=True
):
    """
    画 X-Z 平面上的气压灵敏度热力图。

    拟合定义：
        ΔPressure = sensitivity * Fz + intercept

    sensitivity 单位：
        Pa/N
    """
    if isinstance(data_dirs, str):
        data_dirs = [data_dirs]

    point_data = {}

    for d in data_dirs:
        file_pattern = os.path.join(d, "scan_X*_Z*.csv")
        files = glob.glob(file_pattern)

        if not files:
            print(f"在 {d} 下未找到数据文件")
            continue

        for file in files:
            basename = os.path.basename(file)
            parts = basename.replace('.csv', '').split('_')

            try:
                x_val = int(parts[1][1:])
                z_val = int(parts[2][1:])
            except:
                continue

            try:
                df = pd.read_csv(file)

                sens_press, sens_release, sens_avg, p0 = _fit_press_release_pressure_sensitivity(
                    df,
                    fz_threshold=fz_threshold,
                    pressure_delta_threshold=pressure_delta_threshold,
                    fit_degree=fit_degree,
                    use_abs_mean=use_abs_mean
                )

                if np.isfinite(sens_avg):
                    if (x_val, z_val) not in point_data:
                        point_data[(x_val, z_val)] = []

                    point_data[(x_val, z_val)].append(sens_avg)

            except Exception as e:
                print(f"读取异常 {file}: {e}")

    records = []
    for (x, z), vals in point_data.items():
        if len(vals) > 0:
            records.append({
                'X': x,
                'Z': z,
                'Sensitivity': np.mean(vals)
            })

    df_res = pd.DataFrame(records)

    if df_res.empty:
        print("未提取到有效灵敏度数据。")
        return

    pivot_table = df_res.pivot_table(index='Z', columns='X', values='Sensitivity')

    X_cols = pivot_table.columns.values
    Z_index = pivot_table.index.values

    fig = plt.figure(figsize=(14, 6))

    ax1 = fig.add_subplot(121)
    c = ax1.contourf(
        X_cols,
        Z_index,
        pivot_table.values,
        cmap='viridis',
        levels=20
    )
    fig.colorbar(c, ax=ax1, label='Pressure Sensitivity |dΔP/dFz| (Pa/N)')
    ax1.set_title(
        f'Pressure Sensitivity Distribution\n'
        f'|Fz|>{fz_threshold}N, |ΔP|>{pressure_delta_threshold}Pa'
    )
    ax1.set_xlabel('X Position (mm)')
    ax1.set_ylabel('Z Position (mm)')

    ax2 = fig.add_subplot(122, projection='3d')
    X_mesh, Z_mesh = np.meshgrid(X_cols, Z_index)

    surf = ax2.plot_surface(
        X_mesh,
        Z_mesh,
        pivot_table.values,
        cmap='viridis',
        edgecolor='none'
    )

    fig.colorbar(surf, ax=ax2, shrink=0.5, aspect=0.5, label='Pressure Sensitivity (Pa/N)')
    ax2.set_title('3D Surface of Pressure Sensitivity')
    ax2.set_xlabel('X (mm)')
    ax2.set_ylabel('Z (mm)')
    ax2.set_zlabel('Sensitivity (Pa/N)')

    plt.tight_layout()
    plt.show()

if __name__ == "__main__":
    # 你可以依需要改变为你实际数据的存放路径
    base_folder = os.path.abspath(os.path.join(os.path.dirname(__file__), "../data/scan_2026_5_18"))
    
    # 5_18 下的4个独立测试文件夹，用于求平均
    # data_dirs = [
    #     os.path.join(base_folder, "scan1")
    # ]
    data_dirs = [
        os.path.join(base_folder, "scan1"),
        os.path.join(base_folder, "scan2"),
        os.path.join(base_folder, "scan3"),
        os.path.join(base_folder, "scan4")
    ]
    
    # # print("生成 Max Force 网格热力图...")
    # analyze_and_plot(data_dirs) # 支持传入列表，对对应点的最大值求平均
    
    # # print("生成 Max Fz (ATI) 网格热力图...")
    # analyze_and_plot_fz(data_dirs)
    
    # # 以下功能保持原样，指定其中某一个文件夹的数据源进行绘制，或者也可以自行更改以支持对比
    data_folder = data_dirs[0]  # 这里默认以 scan1 为代表画时序图
    
    
    # # 画 ΔPressure vs Fz
    # plot_pressure_delta_vs_fz(
    #     data_folder,
    #     points=[(211, 83), (218, 83), (214, 83), (220, 79)],
    #     fz_threshold=0.1,
    #     pressure_delta_threshold=100
    # )
    
    # # 画灵敏度热力图
    # plot_pressure_sensitivity_heatmap(
    #     data_dirs,
    #     fz_threshold=0.1,
    #     pressure_delta_threshold=100,
    #     use_abs_mean=True
    # )
    
    # print("生成特定点的 多通道时序比对图...")
    # plot_time_series_comparison(data_folder, points=[(215, 80)])

    # # print("生成特别的 IMU 独立细节分析图...")
    plot_imu_detail(data_folder, points=[(215, 83)])