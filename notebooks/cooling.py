# Functions called in cooling_control.ipynb to run sweeps and feedback control.
"""Utilities for RedPitaya cooling sweeps."""

import pickle
import time
import numpy as np

# Stuff for manual acquisition

class _CurveUnpickler(pickle.Unpickler):
    def find_class(self, module, name):
        raise pickle.UnpicklingError(
            f"global objects are not supported in PyRPL curve files: {module}.{name}"
        )


def load_spectrum_curve(filepath):
    """Load a PyRPL-exported, saved spectrum curve into a two-column NumPy array. The returned columns contain frequency and spectrum values, respectively. """
    with open(filepath, "rb") as curve_file:
        curve = _CurveUnpickler(curve_file).load()

    frequencies = np.asarray(curve[2][0], dtype=float)
    spectrum = np.asarray(curve[2][1], dtype=float)
    return np.column_stack((frequencies, spectrum))

# Stuff for automated cooling control

def sweep_iq_frequency(iq_module, start, end, points, delay):
    """Sweep an IQ module's frequency from start to end, inclusive.
    Args:
        iq_module: Pyrpl IQ module whose ``frequency`` property is updated.
        start: Starting frequency in Hz.
        end: Ending frequency in Hz.
        points: Number of frequency values to apply.
        delay: Delay in seconds between successive frequency updates.

    Returns:  The list of frequencies applied to the IQ module.    """
    if points == 1:
        frequencies = [float(start)]
    else:
        step = (end - start) / (points - 1)
        frequencies = [float(start + index * step) for index in range(points)]
        frequencies[-1] = float(end)

    for index, frequency in enumerate(frequencies):
        iq_module.frequency = frequency
        if index < len(frequencies) - 1:
            time.sleep(delay)
    return frequencies


def sweep_iq_phase(iq_module, start, end, points, delay):
    """Sweep an IQ module's phase from start to end, inclusive.
    Args:
        iq_module: Pyrpl IQ module whose ``phase`` property is updated.
        start: Starting phase in degrees.
        end: Ending phase in degrees.
        points: Number of phase values to apply.
        delay: Delay in seconds between successive phase updates.

    Returns:  The list of phases applied to the IQ module.  """
    if points == 1:
        phases = [float(start)]
    else:
        step = (end - start) / (points - 1)
        phases = [float(start + index * step) for index in range(points)]
        phases[-1] = float(end)

    for index, phase in enumerate(phases):
        iq_module.phase = phase
        if index < len(phases) - 1:
            time.sleep(delay)

    return phases

def measure_spectrum(rp,  frequency_window, input_signal="in1",  window="blackman", averages=1, acbandwidth=0.0,):
    """Acquire a spectrum with PyRPL's IQ DSP block.
    Returns ``(frequencies, amplitudes)`` arrays, 
    Args:
        rp: PyRPL instance or its Red Pitaya interface.
        frequency_window: Two frequencies (start, stop), in Hz.
        input_signal: PyRPL input routed to the spectrum analyzer.
        window: Spectrum window function supported by PyRPL.
        averages: Number of traces to average; use 1 for a single acquisition.
        acbandwidth: IQ module input-filter bandwidth, in Hz. """
    
    start_frequency, stop_frequency = frequency_window
    pyrpl = getattr(rp, "parent", rp)
    analyzer = pyrpl.spectrumanalyzer
    analyzer.setup(input=input_signal, center=(start_frequency + stop_frequency) / 2.0,  baseband=False,
        window=window, acbandwidth=acbandwidth)
    analyzer.trace_average = averages

    frequencies = np.asarray(analyzer.frequencies, dtype=float)
    in_window = (frequencies >= start_frequency) & (frequencies <= stop_frequency)

    spectrum = np.asarray(analyzer.single(), dtype=float)
    return frequencies[in_window], spectrum[in_window]

def measure_peak(rp, target_frequency, search_window, delay=0.0):
    """Return the integrated spectral intensity near target_frequency."""
    time.sleep(delay)
    frequencies, amplitudes = measure_spectrum(
        rp,
        (target_frequency - search_window, target_frequency + search_window),
    )
    frequencies = np.asarray(frequencies, dtype=float)
    amplitudes = np.asarray(amplitudes, dtype=float)
    in_window = np.abs(frequencies - target_frequency) <= search_window
    if np.count_nonzero(in_window) < 2:
        raise ValueError("The peak search window must contain at least two spectrum bins.")
    return float(np.trapz(amplitudes[in_window], x=frequencies[in_window]))


# Need a multivariate gradient descent that has some smoothing / memory of previous tomography.

def minimize_iq_peak(iq_module, rp, target_frequency, search_window, frequency_step, phase_step,
    iterations, delay=0.0,
):
    """Adjust IQ frequency and phase to minimize nearby integrated spectral intensity.
    Args:
        iq_module: IQ module with writable ``frequency`` and ``phase`` values.
        rp: PyRPL instance or its Red Pitaya interface.
        target_frequency: Center frequency of the spectral search window, in Hz.
        search_window: Half-width of the peak search window, in Hz.
        frequency_step: Initial frequency adjustment, in Hz.
        phase_step: Initial phase adjustment, in degrees.
        iterations: Number of hill-climb iterations to perform.
        delay: Seconds to wait after each setting change before acquisition.

    Returns:  Tuple ``(best_frequency, best_phase)`` in Hz and degrees. """
    best_frequency = float(iq_module.frequency)
    best_phase = float(iq_module.phase)
    best_intensity = measure_peak(
        rp, target_frequency, search_window, delay
    )
    try:
        for _ in range(iterations):
            candidates = [
                (best_frequency + frequency_step, best_phase),
                (best_frequency - frequency_step, best_phase),
                (best_frequency, (best_phase + phase_step) % 360.0),
                (best_frequency, (best_phase - phase_step) % 360.0),
            ]
            iteration_best = (best_frequency, best_phase, best_intensity)

            for frequency, phase in candidates:
                iq_module.frequency = frequency
                iq_module.phase = phase
                intensity = measure_peak(
                    rp, target_frequency, search_window, delay
                )
                if intensity < iteration_best[2]:
                    iteration_best = (frequency, phase, intensity)

            if iteration_best[2] < best_intensity:
                best_frequency, best_phase, best_intensity = iteration_best
            else:
                frequency_step /= 2.0
                phase_step /= 2.0
    finally:
        iq_module.frequency = best_frequency
        iq_module.phase = best_phase

    return best_frequency, best_phase