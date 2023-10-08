from collections import deque
import PySimpleGUI as sg
from baseui import BaseUIComponent
import serial.tools.list_ports
from circuits import Component, Event, Timer, Worker, task
from circuits.io.events import close, read, open, write, opened, closed, error
from event import SegmentData, SetSegmentMode, DisplayData
from datetime import datetime
from stransi import Ansi, SetColor

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
            #时间戳
            now = datetime.now().strftime("%m-%d %H:%M:%S.%f")[:-3]
            self.fire(read(data.decode(), now), self.channel)
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
            self._closeflag = False
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
        self._last_hex_time = None
    
    def read(self, *arg):
        data = arg[0]
        if self._mode == "text":
            #文本模式
            for line in data.splitlines(keepends=True):
                #为每行数据增加时间戳
                line = "[" + arg[1] + "] " + line
                self.fire(SegmentData(line, arg[1], "text"), self.channel)
        else :
            #HEX模式,将数据转为hex string
            #每隔50ms分段
            #TODO: 使用component来实现Hex数据的分段
            if self._last_hex_time:
                datetime.now() - self._last_hex_time > 0.05
                self.fire(SegmentData(b"\n", arg[1], "text"), self.channel)
            data = data.hex()
            self.fire(SegmentData(data, arg[1], "hex"), self.channel)
            self._last_hex_time = datetime.now()
    
    def SetSegmentMode(self, *arg):
        pass

class Ansi2DisplayConverter(Component):
    def __init__(self, fg_color="#000000", bg_color="#FFFFFF", channel="serial"):
        super(Ansi2DisplayConverter, self).__init__(channel=channel)
        self.bg_color = bg_color
        self.fg_color = fg_color
        self.default_bg_color = bg_color
        self.default_fg_color = fg_color
        self.bold = False
        #TODO:支持粗体，斜体，下划线
    
    def SetColor(self, bg_color, fg_color):
        self.bg_color = bg_color
        self.fg_color = fg_color
    def SetDefaultColor(self, bg_color, fg_color):
        self.default_bg_color = bg_color
        self.default_fg_color = fg_color
    
    def _cvtColor(self, color):
        return "#{:x}".format(color) 
    
    def SegmentData(self, *arg):
        data = arg[0]
        ts = arg[1]
        mode = arg[2]
        if mode == "hex":
            self.fire(DisplayData(data, ts, self.bg_color, self.fg_color), self.channel)
            return
        for t in Ansi(data).instructions():
            if isinstance(t, str):
                self.fire(DisplayData(t, ts, self.bg_color, self.fg_color), self.channel)
            elif isinstance(t, SetColor):
                if t.role.name == "FOREGROUND":
                    if t.color:
                        self.fg_color = self._cvtColor(t.color.hex.hex_code)
                    else:
                        self.fg_color = self.default_fg_color
                else:
                    if t.color:
                        self.bg_color = self._cvtColor(t.color.hex.hex_code)
                    else:
                        self.bg_color = self.default_bg_color

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
            [sg.I(key="-SENDTEXT-", expand_x=True),sg.B("Send", key="-SEND-")]
        ]
        super().__init__("Serial", self.layout, debug=True)
        self._ser = MySerial()
        self += self._ser
        self += SerialSegmentComponent()
        self._ansi = Ansi2DisplayConverter()
        self += self._ansi
        self += Worker(process=False ,workers=20)

    def updateDisplay(self, win, data, ts, bg_color, fg_color):
        win["-RECVTEXT-"].update(value=data, append=True, text_color_for_value=fg_color, background_color_for_value=bg_color, autoscroll=True)

    def DisplayData(self, data, ts, bg_color, fg_color):
        self.fire(task(self.updateDisplay, self.window, data, ts, bg_color, fg_color))
        # self.window["-RECVTEXT-"].update(value=data, append=True, text_color_for_value=fg_color, background_color_for_value=bg_color, autoscroll=True)
        # self.window.refresh()

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
