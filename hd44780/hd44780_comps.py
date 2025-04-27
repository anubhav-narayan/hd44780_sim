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

