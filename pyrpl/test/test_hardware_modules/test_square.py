from pyrpl.hardware_modules import DSP_INPUTS, DspModule, Sampler, Square, dsp_addr_base
from pyrpl.pyrpl_utils import get_unique_name_list_from_class_list
from pyrpl.redpitaya import RedPitaya
from pyrpl.software_modules import Squares, get_module


def test_square_is_exposed_as_a_dsp_signal():
    assert issubclass(Square, DspModule)
    assert hasattr(Square, "input")
    assert hasattr(Square, "output_direct")
    assert hasattr(Sampler, "square")
    assert DSP_INPUTS["square"] == 8
    assert dsp_addr_base("square") == 0x40380000
    names = get_unique_name_list_from_class_list(RedPitaya.cls_modules)
    assert names[RedPitaya.cls_modules.index(Square)] == "square"
    assert get_module("Squares") is Squares


def test_routing_indices_fit_the_extended_selector():
    assert DSP_INPUTS["in1"] == 11
    assert DSP_INPUTS["in2"] == 12
    assert DSP_INPUTS["out1"] == 13
    assert DSP_INPUTS["out2"] == 14
    assert DSP_INPUTS["iq2_2"] == 15
    assert DSP_INPUTS["off"] == 31
    assert len(set(DSP_INPUTS.values())) == len(DSP_INPUTS)
