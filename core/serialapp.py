from collections import deque
# from baseui import BaseUIComponent
import serial.tools.list_ports
from circuits import Component, Event, Timer, Worker, task, Debugger, ipc
from circuits.io.events import close, read, open, write, opened, closed, error
from circuits.io import File
from event import SegmentData, SetSegmentMode, DisplayData
from datetime import datetime
from stransi import Ansi, SetColor, SetAttribute
from nicegui import ui
from builtins import open as OpenFile

class evtask(Event):
    """
        串口定时处理事件
    """

class evStartRecord(Event):
    """
        开始记录数据
    """

class evStopRecord(Event):
    """
        停止记录数据
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

class Ansi2HtmlConverter(Component):
    def __init__(self, fg_color="black", bg_color="white", channel="serial"):
        super(Ansi2HtmlConverter, self).__init__(channel=channel)
        self.bg_color = bg_color
        self.fg_color = fg_color
        self.default_bg_color = bg_color
        self.default_fg_color = fg_color
        self.bold = False
        self.stroke = False
        self.strong = False
    
    def SetColor(self, bg_color, fg_color):
        self.bg_color = bg_color
        self.fg_color = fg_color
    def SetDefaultColor(self, bg_color, fg_color):
        self.default_bg_color = bg_color
        self.default_fg_color = fg_color
    
    def _cvtColor(self, color):
        # return "#{:x}".format(color) 
        return color.web_color.name
    
    def SegmentData(self, *arg):
        data = arg[0]
        ts = arg[1]
        mode = arg[2]
        if mode == "hex":
            self.fire(DisplayData(data, ts, self.bg_color, self.fg_color), self.channel)
            return
        #html format <p>text<span style="color:fg_color background-color:bg_color">color</span></p>
        #每次处理一行
        html = "<p>"
        for t in Ansi(data).instructions():
            if isinstance(t, str):
                # self.fire(DisplayData(t, ts, self.bg_color, self.fg_color), self.channel)
                if self.bold:
                    fontWeight = "bold"
                else:
                    fontWeight = "normal"
                #TODO: 增加stroke和strong的处理
                html += '<span style="color:{};background-color:{};font-weight:{};">{}</span>'.format(self.fg_color, self.bg_color, fontWeight, t)
            elif isinstance(t, SetAttribute):
                if t.attribute.name == "BOLD":
                    self.bold = True
                elif t.attribute.name == "STROKE":
                    self.stroke = True
                elif t.attribute.name == "STRONG":
                    self.strong = True
                elif t.attribute.name == "NORMAL":
                    self._colorflag = False
                    self.fg_color = self.default_fg_color
                    self.bg_color = self.default_bg_color
                    self.bold = False
                    self.stroke = False
                    self.strong = False
            elif isinstance(t, SetColor):
                if t.role.name == "FOREGROUND":
                    if t.color:
                        self.fg_color = self._cvtColor(t.color)
                    else:
                        self.fg_color = self.default_fg_color
                else:
                    if t.color:
                        self.bg_color = self._cvtColor(t.color)
                    else:
                        self.bg_color = self.default_bg_color
        html += "</p>"
        self.fire(DisplayData(html, ts, self.bg_color, self.fg_color), self.channel)

class FileSaver(Component):
    """
        保存数据(DisplayData)到文件,
        文件格式：串口名_时间戳.log
    """
    channel = "serial"
    def __init__(self, channel="serial"):
        super(FileSaver, self).__init__(channel=channel)
        self.f = None
        self._filename = None
    
    def evStartRecord(self, filename):
        if not filename:
            return   
        if self.f is not None:
            self.f.close()
        self._filename = filename
        self.f = OpenFile(filename, "w", encoding="utf-8")
    
    def evStopRecord(self):
        if self.f is not None:
            self.f.close()
            self.f = None
            self._filename = None
    
    def DisplayData(self, *arg):
        if self.f is None:
            return
        self.f.write(arg[0])


class SerialUI(Component):
    channel = "serial"

    def __init__(self):
        self.baudrates = [
            300, 600, 1200, 2400, 4800, 9600, 14400, 19200, 
            28800, 38400, 56000, 57600, 115200, 128000, 230400,
            256000, 460800, 500000, 512000, 600000, 750000, 921600,
            1000000, 1500000, 2000000, 2500000, 3000000, 3500000
        ]
        ports = serial.tools.list_ports.comports()
        self.port_list = []
        for port in ports:
            self.port_list.append(port.device)
        # super().__init__("Serial", debug=True)
        super().__init__(self.channel)
        # self += Debugger()
        self.port = self.port_list[0]
        self.baud = 115200
        self.openclose = "Open"
        self.sendtxt = ""
        self.recvtxt = ""
        self._ser = MySerial()
        self += self._ser
        self += SerialSegmentComponent()
        self._ansi = Ansi2HtmlConverter()
        self += self._ansi
        self._file = None
        self.record = FileSaver()
        self.record_init = False
        # self += self.record
        # self.record.start()

        #setup ui
        self.topTabs = ui.tabs().classes('w-full')
        self.tabs = []
        with self.topTabs:
            self.tabs.append(ui.tab('Serial-0'))
        self.panels = ui.tab_panels(self.topTabs, value=self.tabs[0]).classes('w-full')
        with self.panels:
            with ui.tab_panel(self.tabs[0]):
                with ui.row().classes("w-full"):
                    #menu
                    self.menu = ui.menu()
                    with ui.button(icon='menu'):
                        with self.menu:
                            ui.menu_item("File")
                            ui.menu_item("Edit")
                            ui.menu_item("Plugins")
                    ui.select(self.port_list, label="Port").bind_value(self, "port")
                    ui.select(self.baudrates, label="Baudrate").bind_value(self,"baud")
                    ui.button(on_click=self.onOpenClose).bind_text(self, "openclose")
                    ui.input().bind_value(self, "sendtxt")
                    ui.button(text="Send", on_click=self.onSend)
                ui.separator()
                # self._log = ui.log().classes("w-full").style("height: 84vh; overflow-y: scroll;")
                self.scroll = ui.scroll_area().classes("w-full").style("height: 84vh;")
                with self.scroll:
                    ui.html().bind_content(self, "recvtxt")
                
                # self._display_queue = deque()
                # self._timer = Timer(0.1, evUpdateUI(), self.channel, persist=True)
                # self += self._timer
    
    def onSend(self):
        # print("send:", self.sendtxt)
        self.fire(write(self.sendtxt.encode()), self._ser.channel)

    def onOpenClose(self, e):
        if not self.running:
            self.start()
        if self.openclose == "Open":
            #保存文件
            if not self.record_init:
                self.record_init = True
                self.record.start(process=True, link=self)
            filename = "./" + self.port + "_" + datetime.now().strftime("%Y_%m_%d_%H_%M_%S") + ".html"
            self.fire(ipc(evStartRecord(filename)), "serial")
            # self.record.startRecord(filename)
            self.fire(open(port=self.port, baudrate=self.baud), self._ser.channel)
            # self._display_queue.append((open(self.port, baudrate=self.baud), self._ser.channel))
            self.openclose = "Close"
        else:
            self.fire(ipc(evStopRecord()), "serial")
            self.record.stopRecord()
            self.fire(close(), self._ser.channel)
            # self._display_queue.append((close(), self._ser.channel))
            self.openclose = "Open"
            if self._file:
                self._file.close()
                self._file = None
    
    def DisplayData(self, data, ts, bg_color, fg_color):
        self.recvtxt += data
        self.scroll.scroll_to(percent=1.0)
        self.fire(ipc(DisplayData(data, ts, bg_color, fg_color)), "serial")

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



if __name__ in {"__main__", "__mp_main__"}:
    myUI = SerialUI()
    myUI.start()
    ui.run(native=True, reload=True)
    myUI.stop()
    myUI.join()
