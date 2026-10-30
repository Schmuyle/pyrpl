import sys
import os

if os.name == "posix": # Force wayland compatibility on linux.
    os.environ["QT_QPA_PLATFORM"] = "xcb" # Force wayland compatibility on linux.

import pyrpl # must happen after setting xcb

HOSTNAME1 = "192.168.68.178"
HOSTNAME2 = "192.168.68.172"

p = pyrpl.Pyrpl(hostname=HOSTNAME2, config="",reloadfpga=True,gui=True)
pyrpl.APP.exec_()