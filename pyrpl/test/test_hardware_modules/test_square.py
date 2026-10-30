from pyrpl import Square1 as PublicSquare1
from pyrpl.hardware_modules import (
    DSP_INPUTS,
    DspModule,
    Sampler,
    Square,
    Square0,
    Square1,
    dsp_addr_base,
)
from pyrpl.pyrpl_utils import get_unique_name_list_from_class_list
from pyrpl.redpitaya import RedPitaya
from pyrpl.software_modules import Squares, get_module
from pyrpl.widgets.module_widgets import SquareWidget


def test_square_is_exposed_as_a_dsp_signal():
    assert issubclass(Square0, DspModule)
    assert Square is Square0
    assert hasattr(Square0, "input")
    assert hasattr(Square0, "output_direct")
    assert hasattr(Sampler, "square0")
    assert hasattr(Sampler, "square1")
    assert DSP_INPUTS["square0"] == 8
    assert DSP_INPUTS["square1"] == 9
    assert dsp_addr_base("square0") == 0x40380000
    assert dsp_addr_base("square1") == 0x40390000
    names = get_unique_name_list_from_class_list(RedPitaya.cls_modules)
    assert names[RedPitaya.cls_modules.index(Square0)] == "square0"
    assert names[RedPitaya.cls_modules.index(Square1)] == "square1"
    assert get_module("Square0") is Square0
    assert PublicSquare1 is Square1
    assert get_module("Squares") is Squares
    assert Square0._widget_class is SquareWidget
    assert Square1._widget_class is SquareWidget
    assert Square0._gui_attributes == ["input", "output_direct"]
    assert Square1._gui_attributes == ["input", "output_direct"]


def test_routing_indices_fit_the_extended_selector():
    assert DSP_INPUTS["asg0"] == 10
    assert DSP_INPUTS["asg1"] == 11
    assert DSP_INPUTS["in1"] == 12
    assert DSP_INPUTS["in2"] == 13
    assert DSP_INPUTS["out1"] == 14
    assert DSP_INPUTS["out2"] == 15
    assert DSP_INPUTS["iq2_2"] == 16
    assert DSP_INPUTS["off"] == 31
    assert len(set(DSP_INPUTS.values())) == len(DSP_INPUTS)
