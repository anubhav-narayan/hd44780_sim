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

from cocotb import logging
from cocotb.triggers import RisingEdge, Timer
from cocotb_bus.bus import Bus
from .hd44780 import HD44780

class HD44780Bus(Bus):
    """
    Cocotb Bus for the HD44780 interface.
    """

    _signals = ["rs", "rw", "e", "db0", "db1", "db2", "db3", "db4", "db5", "db6", "db7"]
    _optional_signals = []

    def __init__(self, entity=None, prefix=None, **kwargs):
       super().__init__(entity, prefix, self._signals, optional_signals=self._optional_signals, **kwargs)


    @classmethod
    def from_prefix(cls, entity, prefix, **kwargs):
        return cls(entity, prefix, **kwargs)


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

    def to_command(self) -> tuple:
        db = 0x00
        for x in range(8):
            db |= (self.db[x] >> x) & 0x1
        return (self.rs, self.rw, db)

    @classmethod
    def from_command(cls, rs, rw, e, db):
        dbl = [0] * 8
        for i in range(8):
            dbl[i] = (db >> i) & 0x1
        return cls(rs, rw, e, *dbl)


class HD44780Sim(HD44780):
    """
    Adds a CoCoTB Coroutine to `HD44780`
    """

    def __init__(
        self, 
        dut, prefix,
        segments=8, lines=1, cols=5, rows=8,
        pixel_size=20, pixel_border=0.2, segment_margin=10, line_margin=20, display_border=20
    ):
        super().__init__(segments, lines, cols, rows, pixel_size, pixel_border, segment_margin, line_margin, display_border)
        self.dut = dut
        self.bus = HD44780Bus.from_prefix(dut, prefix)
        self.log = logging.getLogger('HD44780-Sim')
        self.log.setLevel(logging.DEBUG)
        self.wait_time = 0.037 # Simulated command wait time in ms


    async def get_cmd(self) -> tuple:
        await RisingEdge(self.dut.e)
        pkt = self.bus.capture()
        pkt = HD44780Packet(**pkt)
        return pkt.to_command()

    async def send(self, resp):
        while self.dut.e:
            pkt = HD44780Packet.from_command(self.dut.rs, self.dut.re, self.dut.e, resp)
            self.bus.drive(pkt)

    async def run_coro(self):
        while True:
            command = await self.get_cmd()
            await Timer(self.wait_time/8, 'ms') # 1/8 time to latch
            resp = self.command(*command)
            if resp:
                await self.send(resp)
            else:
                await Timer(7*self.wait_time/8, 'ms')
