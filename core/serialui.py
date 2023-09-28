import PySimpleGUI as sg
from baseui import BaseUIComponent
import serial.tools.list_ports

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
        super().__init__("Serial", self.layout)
        
    def UIEvent(self, *arg):
        event = arg[0]
        values = arg[1]

if __name__ == "__main__":
    serialUI = SerialUI()
    serialUI.run()
