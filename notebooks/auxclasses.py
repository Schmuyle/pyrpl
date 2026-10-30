# These are pure vibe-coded garbage, beware ye all who enter

import numpy as np

from PyQt5.QtCore import QTimer
from PyQt5.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QLabel,
    QDoubleSpinBox,
    QCheckBox,
    QComboBox,
)

from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
from matplotlib.figure import Figure

from pyrpl import Pyrpl

class ASGControlAC(QWidget):
    def __init__(self, rp, output, asgchannel):
        super().__init__()
        # Select ASG channel
        self.rp = rp
        self.asg = asgchannel
        

        # Initial configuration # can optionally put a threshold, rising edge to synchronise the signal...
        self.asg.setup(
            waveform='sin',
            frequency=1000,
            amplitude=0.1,
            offset=0,
            trigger_source='immediately'
        )

        self.asg.output_direct = output
        layout = QVBoxLayout()
        layout.addWidget(QLabel("Frequency (Hz)"))

        self.freq = QDoubleSpinBox()
        self.freq.setRange(0.1, 50e6)
        self.freq.setDecimals(1)
        self.freq.setValue(1000)
        self.freq.setSingleStep(10)
        self.freq.valueChanged.connect(self.update_frequency)
        layout.addWidget(self.freq)

        layout.addWidget(QLabel("Amplitude (V)"))

        self.amp = QDoubleSpinBox()
        self.amp.setRange(0.0, 1.0)
        self.amp.setDecimals(3)
        self.amp.setValue(0.1)
        self.amp.setSingleStep(0.01)
        self.amp.valueChanged.connect(self.update_amplitude)
        layout.addWidget(self.amp)

        self.setLayout(layout)

    def update_frequency(self, value):
        self.asg.frequency = value

    def update_amplitude(self, value):
        self.asg.amplitude = value

class DCBiasControl(QWidget):
    def __init__(self, rp, output,asgchannel):
        super().__init__()
        self.rp = rp
        self.asg = asgchannel

        # Initial DC bias configuration
        try:
            self.asg.setup(
                waveform='dc',
                amplitude=0,
                offset=0,
                trigger_source='immediately'
            )
        except Exception:
            # Fallback if the ASG does not support a dedicated DC waveform
            self.asg.setup(
                waveform='sin',
                amplitude=0,
                offset=0,
                trigger_source='immediately'
            )

        self.asg.output_direct = output

        layout = QVBoxLayout()
        layout.addWidget(QLabel("DC Bias (V)"))

        self.bias = QDoubleSpinBox()
        self.bias.setRange(-1.0, 1.0)
        self.bias.setDecimals(3)
        self.bias.setValue(0.0)
        self.bias.setSingleStep(0.01)
        self.bias.valueChanged.connect(self.update_bias)
        layout.addWidget(self.bias)

        self.setLayout(layout)

    def update_bias(self, value):
        self.asg.offset = value

class IQDemodulatorControl(QWidget):
    def __init__(
        self,
        rp,
        iq_channel,
        scope_monitor=None,
        quadrature_factor=None,
        output_direct=None,
        output_signal=None,
        input_channel=None,
    ):
        super().__init__()
        self.rp = rp
        self.iq = iq_channel
        self.scope_monitor = scope_monitor
        self.quadrature_factor = quadrature_factor
        self.output_direct = output_direct
        self.output_signal = output_signal if output_signal is not None else getattr(self.iq, 'output_signal', 'quadrature')
        self.input_channel = input_channel if input_channel is not None else getattr(self.iq, 'input', 'in1')

        def _safe_float(value, default):
            try:
                return float(value)
            except (TypeError, ValueError):
                return default

        self.frequency_value = _safe_float(getattr(self.iq, 'frequency', 1e6), 1e6)
        self.phase_value = _safe_float(getattr(self.iq, 'phase', 0), 0)
        self.bandwidth_value = _safe_float(getattr(self.iq, 'bandwidth', 1000), 1000)
        self.acbandwidth_value = _safe_float(getattr(self.iq, 'acbandwidth', 1000), 1000)
        self.amplitude_value = _safe_float(getattr(self.iq, 'amplitude', 0.1), 0.1)
        self.gain_value = _safe_float(getattr(self.iq, 'gain', 1.0), 1.0)

        self._apply_setup()

        layout = QVBoxLayout()
        self.setWindowTitle(f"IQ Demodulator Control ({iq_channel.name})")

        self.input_channel_control = QComboBox()
        input_options = list(getattr(self.iq, 'inputs', []))
        if not input_options:
            input_options = ['in1', 'in2', 'iq1', 'iq2']
        self.input_channel_control.addItems(input_options)
        if self.input_channel in input_options:
            self.input_channel_control.setCurrentText(self.input_channel)
        self.input_channel_control.currentTextChanged.connect(self.update_input_channel)
        layout.addWidget(QLabel("Input channel"))
        layout.addWidget(self.input_channel_control)

        self.output_signal_control = QCheckBox("Use output_direct signal")
        self.output_signal_control.setChecked(self.output_signal == 'output_direct')
        self.output_signal_control.toggled.connect(self.update_output_signal)
        layout.addWidget(self.output_signal_control)

        layout.addWidget(QLabel("Frequency (Hz)"))
        self.frequency_control = QDoubleSpinBox()
        self.frequency_control.setRange(0.1, 50e6)
        self.frequency_control.setDecimals(1)
        self.frequency_control.setValue(self.frequency_value)
        self.frequency_control.setSingleStep(10)
        self.frequency_control.valueChanged.connect(self.update_frequency)
        layout.addWidget(self.frequency_control)

        layout.addWidget(QLabel("Phase (degrees)"))
        self.phase = QDoubleSpinBox()
        self.phase.setRange(0, 360)
        self.phase.setDecimals(1)
        self.phase.setValue(self.phase_value)
        self.phase.setSingleStep(1)
        self.phase.valueChanged.connect(self.update_phase)
        layout.addWidget(self.phase)

        layout.addWidget(QLabel("AC Bandwidth (Hz)"))
        self.acbandwidth_control = QDoubleSpinBox()
        self.acbandwidth_control.setRange(1, 1e6)
        self.acbandwidth_control.setDecimals(1)
        self.acbandwidth_control.setValue(self.acbandwidth_value)
        self.acbandwidth_control.setSingleStep(10)
        self.acbandwidth_control.valueChanged.connect(self.update_acbandwidth)
        layout.addWidget(self.acbandwidth_control)

        layout.addWidget(QLabel("Bandwidth (Hz)"))
        self.bandwidth_control = QDoubleSpinBox()
        self.bandwidth_control.setRange(1, 1e6)
        self.bandwidth_control.setDecimals(1)
        self.bandwidth_control.setValue(self.bandwidth_value)
        self.bandwidth_control.setSingleStep(10)
        self.bandwidth_control.valueChanged.connect(self.update_bandwidth)
        layout.addWidget(self.bandwidth_control)

        layout.addWidget(QLabel("Amplitude"))
        self.amplitude_control = QDoubleSpinBox()
        self.amplitude_control.setRange(0.0, 2.0)
        self.amplitude_control.setDecimals(3)
        self.amplitude_control.setValue(self.amplitude_value)
        self.amplitude_control.setSingleStep(0.01)
        self.amplitude_control.valueChanged.connect(self.update_amplitude)
        layout.addWidget(self.amplitude_control)

        layout.addWidget(QLabel("Gain"))
        self.gain = QDoubleSpinBox()
        self.gain.setRange(0.0, 2.0)
        self.gain.setDecimals(3)
        self.gain.setValue(self.gain_value)
        self.gain.setSingleStep(0.01)
        self.gain.valueChanged.connect(self.update_gain)
        layout.addWidget(self.gain)

        self.setLayout(layout)

    def _pause_scope(self):
        if self.scope_monitor:
            self.scope_monitor.pause()

    def _resume_scope(self):
        if self.scope_monitor:
            self.scope_monitor.resume()

    def _build_setup_kwargs(self):
        kwargs = {
            'frequency': self.frequency_value,
            'phase': self.phase_value,
            'gain': self.gain_value,
            'bandwidth': self.bandwidth_value,
            'acbandwidth': self.acbandwidth_value,
            'amplitude': self.amplitude_value,
            'output_signal': self.output_signal,
            'input': self.input_channel,
        }

        if self.quadrature_factor is not None:
            kwargs['quadrature_factor'] = self.quadrature_factor
        if self.output_direct is not None:
            kwargs['output_direct'] = self.output_direct

        return kwargs

    def _apply_setup(self):
        self.iq.setup(**self._build_setup_kwargs())

    def _set_iq_property(self, name, value):
        self._pause_scope()
        try:
            setattr(self.iq, name, value)
        finally:
            self._resume_scope()

    def update_output_signal(self, enabled):
        self.output_signal = 'output_direct' if enabled else 'quadrature'
        self._apply_setup()

    def update_input_channel(self, value):
        self.input_channel = value
        self._apply_setup()

    def update_phase(self, value):
        self._set_iq_property('phase', value)

    def update_frequency(self, value):
        self._set_iq_property('frequency', value)

    def update_acbandwidth(self, value):
        self._set_iq_property('acbandwidth', value)

    def update_bandwidth(self, value):
        self._set_iq_property('bandwidth', value)

    def update_amplitude(self, value):
        self._set_iq_property('amplitude', value)

    def update_gain(self, value):
        self._set_iq_property('gain', value)

class ScopeMonitor(QWidget):
    def __init__(
        self,
        rp,
        input1="in1",
        input2="in2",
        duration=0.01,
        refresh_ms=1000,
    ):
        super().__init__()

        self.rp = rp
        self.scope = rp.scope
        self.duration = duration
        self.is_acquiring = False
        self.is_paused = False
        self.continuous_mode = False

        self.setWindowTitle("Red Pitaya Scope Monitor")
        self.resize(900, 500)

        # ---------------------------
        # Configure scope
        # ---------------------------

        self.scope.input1 = input1
        self.scope.input2 = input2
        self.scope.duration = duration
        self.scope.threshold = 0.0
        self.scope.trigger_source = 'ch1_positive_edge'

        # Note: continuous mode will use scope.continuous(); trigger mode relies on scope single acquisitions
        
        # ---------------------------
        # Matplotlib canvas
        # ---------------------------

        layout = QVBoxLayout(self)

        self.continuous_mode_control = QCheckBox("Continuous acquisition")
        self.continuous_mode_control.setChecked(self.continuous_mode)
        self.continuous_mode_control.toggled.connect(self.set_continuous_mode)
        layout.addWidget(self.continuous_mode_control)

        layout.addWidget(QLabel("Trigger source"))
        self.trigger_source_control = QComboBox()
        trigger_sources = list(getattr(self.scope, 'trigger_sources', []))
        self.trigger_source_control.addItems(trigger_sources)
        current_source = str(getattr(self.scope, 'trigger_source', 'ch1_positive_edge'))
        if current_source in trigger_sources:
            self.trigger_source_control.setCurrentText(current_source)
        self.trigger_source_control.currentTextChanged.connect(self.update_trigger_source)
        layout.addWidget(self.trigger_source_control)

        layout.addWidget(QLabel("Trigger threshold (V)"))
        self.trigger_threshold_control = QDoubleSpinBox()
        self.trigger_threshold_control.setRange(-2.0, 2.0)
        self.trigger_threshold_control.setDecimals(3)
        self.trigger_threshold_control.setSingleStep(0.01)
        self.trigger_threshold_control.setValue(float(getattr(self.scope, 'threshold', 0.0)))
        self.trigger_threshold_control.valueChanged.connect(self.update_trigger_threshold)
        layout.addWidget(self.trigger_threshold_control)

        layout.addWidget(QLabel("Acquisition window (s)"))
        self.duration_control = QDoubleSpinBox()
        self.duration_control.setRange(1e-6, 1.0)
        self.duration_control.setDecimals(6)
        self.duration_control.setSingleStep(1e-4)
        self.duration_control.setValue(float(getattr(self.scope, 'duration', duration)))
        self.duration_control.valueChanged.connect(self.update_duration)
        layout.addWidget(self.duration_control)

        self.figure = Figure()
        self.canvas = FigureCanvasQTAgg(self.figure)

        layout.addWidget(self.canvas)

        self.ax = self.figure.add_subplot(111)

        self.line1, = self.ax.plot([], [], label=input1)
        self.line2, = self.ax.plot([], [], label=input2)

        self.ax.set_xlabel("Time (s)")
        self.ax.set_ylabel("Voltage (V)")
        self.ax.grid(True)
        self.ax.legend(loc='upper left')

        # ---------------------------
        # Update timer ??
        # ---------------------------

        self.timer = QTimer()
        self.timer.timeout.connect(self.update_scope)
        self.timer.start(refresh_ms)

    def pause(self):
        """Pause scope updates."""
        self.is_paused = True

    def resume(self):
        """Resume scope updates."""
        self.is_paused = False

    def update_scope(self):
        """Update scope data - skip if already acquiring or paused to prevent concurrent calls."""
        if self.is_acquiring or self.is_paused:
            return
        
        self.is_acquiring = True
        try:
            if self.continuous_mode:
                if self.scope.running_state not in ["running_continuous", "paused_continuous"]:
                    self.scope.continuous()
                data = self.scope.data_avg
            else:
                if self.scope.running_state != "stopped":
                    self.scope.stop()
                data = self.scope.single()  # single_async seems to be deprecated, API says single() is already asynchronous...

            if data is None:
                return

            ch1 = np.asarray(data[0])
            ch2 = np.asarray(data[1])

            if len(ch1) == 0:
                return

            data_x = getattr(self.scope, 'data_x', None)
            if data_x is not None:
                t = np.asarray(data_x)
            else:
                t = np.linspace(
                    -self.scope.duration / 2,
                    self.scope.duration / 2,
                    len(ch1),
                )

            self.line1.set_data(t, ch1)
            self.line2.set_data(t, ch2)

            ymin = min(ch1.min(), ch2.min())
            ymax = max(ch1.max(), ch2.max())

            if ymax == ymin:
                ymax += 0.1
                ymin -= 0.1

            margin = 0.1 * (ymax - ymin)

            self.ax.set_xlim(t[0], t[-1])
            self.ax.set_ylim(
                ymin - margin,
                ymax + margin,
            )

            self.canvas.draw_idle()

        except Exception as exc:
            print(f"Scope update failed: {exc}")
        finally:
            self.is_acquiring = False

    def set_channels(self, input1, input2):
        self.scope.input1 = input1
        self.scope.input2 = input2

        self.line1.set_label(input1)
        self.line2.set_label(input2)

        self.ax.legend(loc='upper left')
        self.canvas.draw_idle()

    def set_duration(self, duration):
        self.scope.setup(duration=duration)
        self.duration_control.setValue(duration)

    def set_refresh_rate(self, refresh_ms):
        self.timer.setInterval(refresh_ms)

    def update_trigger_threshold(self, value):
        self._apply_scope_setup(threshold=value)

    def update_duration(self, value):
        self._apply_scope_setup(duration=value)

    def update_trigger_source(self, value):
        self._apply_scope_setup(trigger_source=value)

    def set_continuous_mode(self, enabled):
        self.continuous_mode = enabled
        self.trigger_threshold_control.setEnabled(not enabled)
        self.trigger_source_control.setEnabled(not enabled)
        if enabled:
            self.scope.setup(trigger_source='immediately')
            self.scope.continuous()
        else:
            self.scope.stop()
            self.scope.setup(trigger_source=self.trigger_source_control.currentText())

    def _apply_scope_setup(self, **kwargs):
        self.scope.setup(**kwargs)
        if self.continuous_mode:
            try:
                self.scope.stop()
            except Exception:
                pass
            self.scope.continuous()

    def closeEvent(self, event):

        self.timer.stop()

        try:
            self.scope.stop()
        except Exception:
            pass

        event.accept()

# Add manual control to the frequency and phase of the IQ demodulator modula 