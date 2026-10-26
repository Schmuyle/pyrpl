from .dsp import DspModule


class Square(DspModule):
    """Square the selected signed Q1.13 DSP input.

    The output is scaled back to Q1.13, saturated at the largest positive
    representable value, and delayed by one FPGA clock cycle.

    Example:

        rp.square.input = "in1"
        rp.square.output_direct = "out1"
        rp.pid0.input = "square"
    """

