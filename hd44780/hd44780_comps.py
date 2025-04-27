"""
CoCoTB components for the Software model of the Hitachi HD44780 LCD Controller.
Copyright (C) 2025  Anubhav Mattoo

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <https://www.gnu.org/licenses/>.
"""

import cocotb
from cocotb_bus.bus import Bus

class HD44780Bus(Bus):
    """
    Cocotb Bus for the HD44780 interface.
    """

    _signals = ["RS", "RW", "E", "DB0", "DB1", "DB2", "DB3", "DB4", "DB5", "DB6", "DB7"]



class HD44780Packet():
    """
    Packet for HD44780
    """
    def __init__(self, rs=0, rw=0, e=0,
                 db0=0, db1=0, db2=0, db3=0,
                 db4=0, db5=0, db6=0, db7=0) -> None:
        self.rs = rs
        self.rw = rw
        self.e = e
        self.db = [db0, db1, db2, db3, db4, db5, db6, db7]


    def __repr__(self) -> str:
        rstr = ''
        rstr += f'RS   : {self.rs:1b}\n'
        rstr += f'RW   : {self.rw:1b}\n'
        rstr += f'E    : {self.e:1b}\n'
        rstr += f'BUSY : {self.db[7]:1b}\n'
        for x in range(8):
            rstr += f'DB{7-x:1d}  : {self.db[7-x]:1b}\n'
        return rstr

