import os
import re
import glob
import json
import numpy as np
import matplotlib.pyplot as plt

plt.style.use('Solarize_Light2')
plt.rcParams['axes.prop_cycle'] = plt.cycler(color=plt.cm.viridis(np.linspace(0, 1, 5)))

# Directorio donde están elev_*.bin, time_*.txt y coordenadas (mismo que plot.py o explícito)
script_dir = os.path.dirname(os.path.abspath(__file__))
config_path = os.path.join(script_dir, '..', 'setup', 'config.json')
with open(config_path, 'r') as f:
    config = json.load(f)

nx = config['WIDTH']
ny = config['HEIGHT']
dx = config['dx']
dy = config['dy']
x = np.arange(nx) * dx
y = np.arange(ny) * dy
center_y = ny // 2

def sort_numeric(files):
    return sorted(files, key=lambda p: int(re.search(r'(\d+)', os.path.basename(p)).group(1)))

elev_files = sort_numeric(glob.glob(os.path.join(script_dir, 'elev_*.bin')))
time_files = sort_numeric(glob.glob(os.path.join(script_dir, 'time_*.txt')))
n_frames = min(len(elev_files), len(time_files))
elev_files = elev_files[:n_frames]
time_files = time_files[:n_frames]

def load_bin(path):
    return np.fromfile(path, dtype=np.float32).reshape((ny, nx))

times = np.array([float(np.loadtxt(tf)) for tf in time_files])

# Matriz elevación (tiempo x posiciones x) para heatmap
elevation_matrix = np.zeros((n_frames, nx))
for i in range(n_frames):
    eta = load_bin(elev_files[i])
    elevation_matrix[i, :] = eta[center_y, :]

# --- Heatmap: tiempo vs x ---
plt.figure(dpi=400)
heatmap = plt.imshow(elevation_matrix, aspect='auto', extent=[x[0], x[-1], times[0], times[-1]], origin='lower', cmap='viridis')
plt.colorbar(heatmap, label=r'$\eta$ [m]')
plt.xlabel(r'$x$ [m]')
plt.ylabel(r'$t$ [s]')
plt.grid(False)
plt.tight_layout()
plt.savefig(os.path.join(script_dir, 'heatmap_elevacion_x_tiempo.png'), bbox_inches='tight', dpi=300)
plt.show()

# --- Curtosis de alturas de ola en el tiempo ---
def identify_waves(elevation_data, mean_level=0.0):
    zero_crossings = np.where(np.diff(np.sign(elevation_data - mean_level)))[0]
    wave_heights = []
    for i in range(len(zero_crossings) - 1):
        segment = elevation_data[zero_crossings[i]:zero_crossings[i + 1]]
        crest = np.max(segment)
        trough = np.min(segment)
        wave_heights.append(crest - trough)
    return np.array(wave_heights)

spatial_kurtosis = []
for i in range(n_frames):
    eta_center = elevation_matrix[i, :]
    wave_heights = identify_waves(eta_center)
    if len(wave_heights) > 0:
        mean_val = np.mean(wave_heights)
        std_val = np.std(wave_heights)
        m4 = np.mean((wave_heights - mean_val) ** 4)
        kurtosis_val = np.nan_to_num(m4 / (std_val ** 4), nan=0.0, posinf=0.0, neginf=0.0)
    else:
        kurtosis_val = 0.0
    spatial_kurtosis.append(kurtosis_val)

plt.figure(figsize=(12, 6))
plt.plot(times, spatial_kurtosis, 'r-', linewidth=2)
plt.xlabel('Tiempo (s)')
plt.ylabel('Curtosis de alturas de ola')
plt.title('Evolución de la curtosis de alturas de ola')
plt.grid(True)
plt.tight_layout()
plt.savefig(os.path.join(script_dir, 'curtosis_alturas_ola.png'), bbox_inches='tight')
plt.show()

# --- Perfil central (último instante) ---
eta_last = elevation_matrix[-1, :]
plt.figure(figsize=(12, 5))
plt.plot(x, eta_last, '-', color='black', linewidth=2)
plt.xlabel('Distancia X (m)')
plt.ylabel('Elevación (m)')
plt.grid(True)
plt.xlim(x.min(), x.max())
eta_margin = max(0.01, (eta_last.max() - eta_last.min()) * 0.1)
plt.ylim(eta_last.min() - eta_margin, eta_last.max() + eta_margin)
plt.tight_layout()
plt.savefig(os.path.join(script_dir, 'evolucion_superficie_libre.png'), dpi=100, bbox_inches='tight')
plt.show()

# --- Boyas: posiciones desde config, series desde elev_*.bin ---
loc_ts = config.get('locationOfTimeSeries', [])
n_gauges_max = min(8, len(loc_ts)) if loc_ts else 0
if n_gauges_max > 0:
    x_gauge_positions = np.array([float(loc_ts[k]['xts']) for k in range(n_gauges_max)])
else:
    x_gauge_positions = np.array([0.0, 10.0, 20.0, 30.0, 40.0, 50.0, 60.0, 70.0])
y_gauge = y[center_y]
gauge_indices = np.argmin(np.abs(x.reshape(-1, 1) - x_gauge_positions), axis=0)
gauge_x_actual = x[gauge_indices]
gauge_time_series = [elevation_matrix[:, gauge_indices[k]] for k in range(len(gauge_x_actual))]

with open(os.path.join(script_dir, 'gauge_time_series.txt'), 'w') as f:
    f.write("# Posiciones de boyas (X, Y) [m]\n")
    f.write("# Formato: X\tY\n")
    for x_actual in gauge_x_actual:
        f.write(f"{x_actual:.6f}\t{y_gauge:.6f}\n")
    f.write("\n# Series de tiempo\n")
    f.write("# Formato: Time[s]")
    for idx in range(len(gauge_indices)):
        f.write(f"\tEta{idx+1}[m]")
    f.write("\n")
    for t_idx, t in enumerate(times):
        f.write(f"{t:.10f}")
        for series in gauge_time_series:
            f.write(f"\t{series[t_idx]:.10f}")
        f.write("\n")

n_gauges = len(gauge_x_actual)
xlim_left = float(times[0]) - 0.5
xlim_right = float(times[-1]) + 0.5
fig, axes = plt.subplots(n_gauges, 1, figsize=(8, 8), dpi=150, sharex=True)
for idx in range(n_gauges):
    axes[idx].plot(times, gauge_time_series[idx], '-', linewidth=2, color=f'C{idx}')
    axes[idx].set_ylabel(r'$\eta$ [m]')
    axes[idx].grid(True)
    axes[idx].set_xlim(xlim_left, xlim_right)
axes[-1].set_xlabel('Time [s]')
plt.tight_layout()
plt.savefig(os.path.join(script_dir, 'series_tiempo_boyas.png'), dpi=300, bbox_inches='tight')
plt.show()

plt.figure(figsize=(8, 4), dpi=150)
plt.plot(times, gauge_time_series[0], 'r-', linewidth=2, label=f'Celeris (X = {gauge_x_actual[0]:.2f} m)', alpha=0.8)
plt.xlabel('Time [s]')
plt.ylabel(r'$\eta$ [m]')
plt.legend(loc='upper right')
plt.grid(True)
plt.xlim(xlim_left, xlim_right)
plt.tight_layout()
plt.savefig(os.path.join(script_dir, 'comparacion_primera_boya.png'), dpi=300, bbox_inches='tight')
plt.show()

print("Gráficos guardados en", script_dir)
