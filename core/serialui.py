import PySimpleGUI as sg
from baseui import BaseUIComponent
import serial.tools.list_ports
from circuits.io.serial import Serial, _open
from circuits.io.events import close

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
        self._ser = None
        
    def UIEvent(self, *arg):
        event = arg[0]
        values = arg[1]
        if event == "-OPENCLOSE-":
            if self.window["-OPENCLOSE-"].GetText() == "Open":
                #判断串口是否存在
                if not values['-PORTLIST-']:
                    return
                #打开串口
                if self._ser is None:
                    #第一次打开
                    self._ser = Serial(values["-PORTLIST-"], int(values["-BAUDRATELIST-"]))
                    self += self._ser
                else:
                    #再次打开, 先发送关闭事件, 然后发送_open 事件
                    self.fire(close(), self._ser.channel)
                    self.fire(_open(port=values["-PORTLIST-"], baudrate=int(values["-BAUDRATELIST-"])), self._ser.channel)
                self.window["-OPENCLOSE-"].update(text="Close")
                self.window.refresh()
            else:
                self.fire(close(), self._ser.channel)
                self.window["-OPENCLOSE-"].update(text="Open")
                self.window.refresh()

if __name__ == "__main__":
    serialUI = SerialUI()
    serialUI.uiRun()
