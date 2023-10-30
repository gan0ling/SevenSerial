from core.plugintype import SourceActor
import time, serial
from datetime import datetime
import logging

class SerialSourceActor(SourceActor):
    def __init__(self):
        super().__init__(timeout=0.01, block=False)
        self.port = None
        self.baudrate = 115200
        self.serial = None

    def on_poll(self) -> None:
        if self.serial and self.serial.is_open and self.serial.in_waiting:
            data = self.serial.read(self.serial.in_waiting).decode('utf-8', errors='ignore')
            #发布消息，topic为/serial/read data为data ts为当前时间戳
            now = datetime.now().strftime("%m-%d %H:%M:%S.%f")[:-3]
            self.tell({'port':self.port,'data': data, 'ts': now})
        else:
           time.sleep(self.timeout)

    def on_open(self, message):
        """
        打开串口, 若之前已经打开，则先关闭
            message: 字典
                topic: 字符串
                port: 字符串
                baudrate: 波特率
                timeout: float
        """
        if self.serial and self.serial.is_open:
            self.serial.close()
            self.serial = None
        self.port = message.get('port')
        self.baudrate = message.get('baudrate')
        self.timeout = message.get('timeout', self.timeout)
        self.serial = serial.Serial(self.port, self.baudrate, timeout=self.timeout)

    def on_close(self, message):
        if self.serial and self.serial.is_open:
            self.serial.close()
        self.serial = None

    def on_write(self, message):
        if self.serial and self.serial.is_open:
            data = message.get('data')
            self.serial.write(data)

    def on_cmd(self, msg):
        if 'cmd' not in msg:
            return
        cmd = msg['cmd']
        if cmd == 'open':
            self.on_open(msg)
        elif cmd == 'close':
            self.on_close(msg)
        elif cmd == 'write':
            self.on_write(msg)
    
    def on_input(self, msg):
        self.on_write(msg)
