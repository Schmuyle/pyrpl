from ..widgets.module_widgets import SquareWidget
from .dsp import DspModule


class Square0(DspModule):
    """Square the selected signed Q1.13 DSP input.

    The output is scaled back to Q1.13, saturated at the largest positive
    representable value, and delayed by one FPGA clock cycle.

    Example:

        rp.square0.input = "in1"
        rp.square0.output_direct = "out1"
        rp.square1.input = "square0"
        rp.pid0.input = "square1"
    """

    _widget_class = SquareWidget
    _setup_attributes = ["input", "output_direct"]
    _gui_attributes = _setup_attributes


class Square1(Square0):
    """Second independent squaring block."""


Square = Square0
