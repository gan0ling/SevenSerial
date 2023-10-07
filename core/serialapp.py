from collections import deque
import PySimpleGUI as sg
from baseui import BaseUIComponent
import serial.tools.list_ports
from circuits import Component, Event, Timer
from circuits.io.events import close, read, open, write, opened, closed, error
from event import SegmentData, SetSegmentMode

class evtask(Event):
    """
        串口定时处理事件
    """

class MySerial(Component):
    """
        定时从串口读取数据
    """
    channel = "serial"
    def __init__(self, port=None, baudrate=115200, timeout=0.05, bufsize=4096):
        super().__init__()
        self.port = port
        self.baudrate = baudrate
        self.timeout = timeout
        self.bufsize = bufsize
        self._ser = None
        self._wrbuf = deque()
        self._closeflag = False
        self._timer = None
    
    def open(self, port=None, baudrate=None, bufsize=None):
        self.port = port or self.port
        self.baudrate = baudrate or self.baudrate
        self.bufsize = bufsize or self.bufsize

        #如果串口相同，不需要重新打开
        if self._ser is not None and self._ser.port == self.port and self._ser.baudrate == self.baudrate:
            return
        #如果不相同，关闭之前的串口
        if self._ser is not None:
            self._ser.close()
            self._ser = None
        self._ser = serial.Serial(port=self.port, baudrate=self.baudrate, timeout=self.timeout)
        self.fire(opened(self.port, self.baudrate), self.channel)
        #打开timer
        self._timer = Timer(self.timeout, evtask(), self.channel, persist=True)
        self += self._timer


    def close(self):
        #关闭串口, 将_closeflag设置为True, 等待process函数中检测到后关闭
        if not self._closeflag:
            self._closeflag = True

    def write(self, data):
        self._wrbuf.append(data)

    def evtask(self):
        #从串口读取数据
        if self._ser is None:
            return
        if self._ser.in_waiting > 0:
            data = self._ser.read(self._ser.in_waiting)
            self.fire(read(data), self.channel)
        #发送数据
        if self._wrbuf:
            try:
                data = self._wrbuf.popleft()
                try:
                    nbytes = self._ser.write(data)
                except serial.SerialTimeoutException:
                    nbytes = 0 
                if nbytes < len(data):
                    self._wrbuf.appendleft(data[nbytes:])
            except (OSError, IOError) as e:
                self.fire(error(e))
                self.close()
        #判断closeflag, 如果为True, 关闭串口
        if self._closeflag:
            self._ser.close()
            self._ser = None
            if self._timer is not None:
                self._timer.unregister()
                self._timer = None

class SerialSegmentComponent(Component):
    """
    将数据分段：
    1. 文本模式下，按照行来分段，并且增加时间戳
    2. Hex模式下， 按照时间来分段, 默认50ms
    Output事件：
        SegmentData
    Input事件
        SetSegmentMode: 设置分段模式
        read: 读数据
    """
    channel = "serial"
    def __init__(self, mode="text", channel="serial"):
        super(SerialSegmentComponent, self).__init__(channel=channel)
        self._mode = mode
    
    def read(self, *arg):
        print("read:", arg)
        if self._mode == "text":
            #文本模式
            pass
        else :
            #HEX模式
            pass
    
    def SetSegmentMode(self, *arg):
        pass


class SerialUI(BaseUIComponent):
    def __init__(self):
        self.baudrates = [
            "300", "600", "1200", "2400", "4800", "9600", "14400", "19200", 
            "28800", "38400", "56000", "57600", "115200", "128000", "230400",
            "256000", "460800", "500000", "512000", "600000", "750000", "921600",
            "1000000", "1500000", "2000000", "2500000", "3000000", "3500000"
        ]
        ports = serial.tools.list_ports.comports()
        port_list = []
        for port in ports:
            port_list.append(port.device)
        self.layout = [
            [sg.T("Port:"), sg.Combo(port_list, key="-PORTLIST-", enable_events=True), sg.T("Baudrate:"), sg.Combo(self.baudrates, default_value="115200", key="-BAUDRATELIST-", enable_events=True), sg.B("Open", key="-OPENCLOSE-")],
            [sg.Multiline(size=(100, 50), key="-RECVTEXT-", expand_x=True, expand_y=True)],
            [sg.I(key="-SENDTEXT-"),sg.B("Send", key="-SEND-")]
        ]
        super().__init__("Serial", self.layout, debug=True)
        self._ser = MySerial()
        self += self._ser
        
    def UIEvent(self, *arg):
        event = arg[0]
        values = arg[1]
        if event == "-OPENCLOSE-":
            if self.window["-OPENCLOSE-"].GetText() == "Open":
                #判断串口是否存在
                if not values['-PORTLIST-']:
                    return
                #打开串口
                self.fire(open(port=values["-PORTLIST-"], baudrate=int(values["-BAUDRATELIST-"])), self._ser.channel)
                self.window["-OPENCLOSE-"].update(text="Close")
                self.window.refresh()
            else:
                self.fire(close(), self._ser.channel)
                self.window["-OPENCLOSE-"].update(text="Open")
                self.window.refresh()

if __name__ == "__main__":
    serialUI = SerialUI()
    serialUI.uiRun()
