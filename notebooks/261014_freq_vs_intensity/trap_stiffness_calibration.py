""" Reads the already recorded spectra from pyrpl, maps filename voltages to laser power, and plot up to three peak frequencies per file."""

import csv
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
from scipy.signal import find_peaks
from scipy.constants import Boltzmann as k_B

import cooling

script_dir = Path(__file__).resolve().parent
spectra_dir = script_dir / "intensity_calibration_sweep"
power_levels_csv = spectra_dir / "power_levels.csv"
peak_threshold = None  # SciPy threshold: minimum vertical distance from each peak to its neighbors.
peak_search_window = (30000, 200000)  # (start_Hz, stop_Hz), or None to search all frequencies.
max_peaks = 3
smoothing_sigma_points = 1.0  # Gaussian FFT smoothing scale in frequency bins.
area_to_J_per_Hz_factor = 1.0  # Placeholder: replace with calibrated J/Hz per (Vpk^2 Hz).
peak_records = []
spectrum_records = []


def fourier_smooth(values, sigma_points):
    if sigma_points < 0:
        raise ValueError("smoothing_sigma_points must be non-negative")
    if sigma_points == 0:
        return values.copy()
    padding = int(np.ceil(4 * sigma_points))
    padded_values = np.pad(values, padding, mode="reflect")
    frequencies = np.fft.rfftfreq(padded_values.size)
    gaussian_filter = np.exp(-2 * np.pi**2 * sigma_points**2 * frequencies**2)
    return np.fft.irfft(np.fft.rfft(padded_values) * gaussian_filter, n=padded_values.size)[padding:-padding]


with power_levels_csv.open(newline="", encoding="utf-8-sig") as csv_file:
    reader = csv.reader(csv_file)
    next(reader, None)  # Skip the header row; columns are positional below.
    laser_power_by_voltage = {}
    for row_number, row in enumerate(reader, start=2):
        if len(row) < 2:
            raise ValueError(f"Expected at least two columns on CSV row {row_number}")
        voltage = float(row[0])
        laser_power_mW = float(row[1])
        if voltage in laser_power_by_voltage:
            raise ValueError(f"Duplicate voltage_mV entry in {power_levels_csv}: {voltage}")
        laser_power_by_voltage[voltage] = laser_power_mW

calibration_voltages_mV = np.array(sorted(laser_power_by_voltage))
calibration_powers_mW = np.array([laser_power_by_voltage[voltage] for voltage in calibration_voltages_mV])

for file_path in sorted(spectra_dir.glob("*.dat")):
    stem = file_path.stem
    lower_stem = stem.lower()
    if lower_stem.endswith("mv"):
        voltage_mV = float(stem[:-2])
    elif lower_stem.endswith("v"):
        voltage_mV = float(stem[:-1]) * 1000.0
    else:
        voltage_mV = float(stem)  # Bare numeric filenames are assumed to be mV.
    if voltage_mV not in laser_power_by_voltage:
        raise KeyError(f"No laser power mapping for {voltage_mV} mV (spectrum {file_path.name})")
    laser_power_mW = laser_power_by_voltage[voltage_mV]

    curve = cooling.load_spectrum_curve(file_path)
    frequencies = curve[:, 0]
    power = curve[:, 1]
    spectrum_valid = np.isfinite(frequencies) & np.isfinite(power)
    if peak_search_window is not None:
        start_hz, stop_hz = peak_search_window
        spectrum_valid &= (frequencies >= start_hz) & (frequencies <= stop_hz)
    finite_frequencies = frequencies[spectrum_valid]
    smoothed_power = fourier_smooth(power[spectrum_valid], smoothing_sigma_points)
    spectrum_records.append({"file": file_path.name, "laser_power_mW": laser_power_mW, "frequencies_Hz": finite_frequencies, "power_Vpk2": smoothed_power})
    selected_indices = np.flatnonzero(spectrum_valid)
    smoothed_valid_power = fourier_smooth(power[selected_indices], smoothing_sigma_points)
    peak_indices, _ = find_peaks(smoothed_valid_power, threshold=peak_threshold, distance=5000)
    strongest_peaks = peak_indices[
        np.argsort(smoothed_valid_power[peak_indices])[-max_peaks:]
    ]
    strongest_peaks = strongest_peaks[
        np.argsort(frequencies[selected_indices[strongest_peaks]])
    ]
    raw_valid_power = power[selected_indices]
    for peak_number, peak_index in enumerate(strongest_peaks, start=1):
        raw_peak_height = raw_valid_power[peak_index]
        ten_percent_height = 0.1 * raw_peak_height
        left_index = peak_index
        while left_index > 0 and raw_valid_power[left_index] > ten_percent_height:
            left_index -= 1
        if left_index == 0 and raw_valid_power[left_index] > ten_percent_height:
            left_frequency = frequencies[selected_indices[0]]
        else:
            left_fraction = (ten_percent_height - raw_valid_power[left_index]) / (raw_valid_power[left_index + 1] - raw_valid_power[left_index])
            left_frequency = frequencies[selected_indices[left_index]] + left_fraction * (frequencies[selected_indices[left_index + 1]] - frequencies[selected_indices[left_index]])
        right_index = peak_index
        while right_index < len(raw_valid_power) - 1 and raw_valid_power[right_index] > ten_percent_height:
            right_index += 1
        if right_index == len(raw_valid_power) - 1 and raw_valid_power[right_index] > ten_percent_height:
            right_frequency = frequencies[selected_indices[right_index]]
        else:
            right_fraction = (ten_percent_height - raw_valid_power[right_index - 1]) / (raw_valid_power[right_index] - raw_valid_power[right_index - 1])
            right_frequency = frequencies[selected_indices[right_index - 1]] + right_fraction * (frequencies[selected_indices[right_index]] - frequencies[selected_indices[right_index - 1]])
        inside_width = (frequencies[selected_indices] > left_frequency) & (frequencies[selected_indices] < right_frequency)
        integration_frequencies = np.concatenate(([left_frequency], frequencies[selected_indices][inside_width], [right_frequency]))
        integration_power = np.interp(integration_frequencies, frequencies[selected_indices], raw_valid_power)
        peak_area_Vpk2_Hz = np.trapezoid(integration_power, integration_frequencies)
        peak_records.append({"file": file_path.name, "voltage_mV": voltage_mV, "laser_power_mW": laser_power_mW, "peak_number": peak_number, "frequency_Hz": float(frequencies[selected_indices[peak_index]]), "power_Vpk2": float(smoothed_valid_power[peak_index]), "width_10pct_Hz": float(right_frequency - left_frequency), "area_Vpk2_Hz": float(peak_area_Vpk2_Hz), "temperature_K": float(frequencies[selected_indices[peak_index]] * peak_area_Vpk2_Hz * area_to_J_per_Hz_factor / k_B)})

if not peak_records:
    raise FileNotFoundError(f"No .dat spectrum files found in {spectra_dir}")

peak_records.sort(key=lambda record: (record["laser_power_mW"], record["frequency_Hz"]))

fig, axes = plt.subplots(1, 3, figsize=(18, 6))
frequency_axis = axes[0]
voltage_frequency_axis = axes[1]
temperature_axis = axes[2]
peak_numbers = sorted({record["peak_number"] for record in peak_records})
peak_colors = plt.get_cmap("tab10")
equation_lines = []
for peak_number in peak_numbers:
    peak_data = [record for record in peak_records if record["peak_number"] == peak_number]
    peak_power_values = np.array([record["laser_power_mW"] for record in peak_data])
    peak_voltage_values = np.array([record["voltage_mV"] for record in peak_data])
    peak_frequency_values = np.array([record["frequency_Hz"] for record in peak_data])
    peak_intensity_values = np.array([record["power_Vpk2"] for record in peak_data])
    peak_temperature_values = np.array([record["temperature_K"] for record in peak_data])
    color = peak_colors((peak_number - 1) % 10)
 
    frequency_axis.scatter(peak_power_values, peak_frequency_values,color=color,label=f"Peak {peak_number}")
    voltage_frequency_axis.scatter(peak_voltage_values,peak_frequency_values,color=color,label=f"Peak {peak_number}")
    temperature_axis.scatter(peak_power_values,peak_temperature_values,color=color,label=f"Peak {peak_number}")

    if np.unique(peak_power_values).size >= 2:
        slope, intercept = np.polyfit(peak_power_values, peak_frequency_values, 1)
        trend_x = np.linspace(peak_power_values.min(), peak_power_values.max(), 100)
        frequency_axis.plot(trend_x, slope * trend_x + intercept, color=color, linestyle="--")
        equation_lines.append(f"Peak {peak_number}: f = {slope:.3g} P {intercept:+.3g}")

        temperature_slope, temperature_intercept = np.polyfit(peak_power_values, peak_temperature_values, 1)
        temperature_axis.plot(trend_x, temperature_slope * trend_x + temperature_intercept, color=color, linestyle="--")
        temperature_axis.text(0.02, 0.98 - (peak_number - 1) * 0.06, f"Peak {peak_number}: T = {temperature_slope:.3g} P {temperature_intercept:+.3g}", transform=temperature_axis.transAxes, color=color, fontsize=9, va="top")
    else:
        equation_lines.append(f"Peak {peak_number}: not enough power values to fit")

frequency_axis.set_xlabel("Laser power (mW)")
frequency_axis.set_ylabel("Peak frequency (Hz)")
frequency_axis.tick_params(axis="y")
frequency_axis.grid(True)
frequency_axis.set_title("Peak frequency vs. laser power")
for line_number, equation in enumerate(equation_lines):
    frequency_axis.text(0.02, 0.98 - line_number * 0.06, equation, transform=frequency_axis.transAxes, color=peak_colors((peak_numbers[line_number] - 1) % 10), fontsize=9, va="top")

voltage_frequency_axis.set_xlabel("Voltage (mV)")
voltage_frequency_axis.set_ylabel("Peak frequency (Hz)")
voltage_frequency_axis.set_title("Peak frequency vs. voltage")
voltage_frequency_axis.grid(True)
voltage_frequency_axis.legend(loc="best")

temperature_axis.set_xlabel("Laser power (mW)")
temperature_axis.set_ylabel("Temperature (K; placeholder area calibration)")
temperature_axis.set_title("Temperature vs. laser power")
temperature_axis.grid(True)
temperature_axis.legend(loc="best")

frequency_axis.legend(loc="best")
fig.tight_layout()
#plt.show()

voltage_power_fig, voltage_power_axis = plt.subplots(figsize=(8, 5))
voltage_power_axis.plot(calibration_voltages_mV, calibration_powers_mW, marker="o")
voltage_power_axis.set_xlabel("Voltage (mV)")
voltage_power_axis.set_ylabel("Laser power (mW)")
voltage_power_axis.set_title("Laser power vs. voltage")
voltage_power_axis.grid(True)
voltage_power_fig.tight_layout()

spectra_fig, spectra_axis = plt.subplots(figsize=(10, 6))
for spectrum_record in spectrum_records:
    spectra_axis.plot(spectrum_record["frequencies_Hz"], spectrum_record["power_Vpk2"], label=f'{spectrum_record["laser_power_mW"]:g} mW')
spectra_axis.set_xlabel("Frequency (Hz)")
spectra_axis.set_ylabel("Intensity (Vpk^2)")
spectra_axis.set_title("Overlaid spectra")
spectra_axis.grid(True)
spectra_axis.legend(title="Laser intensity", loc="best")
spectra_fig.tight_layout()
plt.show()

peak_records
