from collections import deque
import serial.tools.list_ports
from datetime import datetime
from manager import ActorManager
from coreplugin import SerialPlugin, SerialSegmentPlugin, Ansi2HtmlConverter, FileSaver
from nicegui import ui, app
import logging, signal
import pykka.debug

class SerialUI(object):
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
        super().__init__()
        self.port = self.port_list[0]
        self.baud = 115200
        self.openclose = "Open"
        self.sendtxt = ""
        self.recvtxt = ""
        self._ser_ref = None
        self._segment_ref = None
        self._conver_ref = None
        self._saver_ref = None
        ActorManager.singleton().subscribe('/data/display_data', self)
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


    def onSend(self):
        m = ActorManager.singleton()
        m.tell("/serial/write", {'data':self.sendtxt}, actor_ref=self._ser_ref)

    def onOpenClose(self, e):
        m = ActorManager.singleton()
        if not self._ser_ref:
            self._ser_ref = SerialPlugin.start(port=self.port, baudrate=self.baud)
        if not self._segment_ref:
            self._segment_ref = SerialSegmentPlugin.start()
        if not self._conver_ref:
            self._conver_ref = Ansi2HtmlConverter.start()
        if not self._saver_ref:
            self._saver_ref = FileSaver.start()
        if self.openclose == "Open":
            #保存文件
            filename = "./log/" + self.port + "_" + datetime.now().strftime("%Y_%m_%d_%H_%M_%S") + ".html"
            m.tell("/file_saver/start_record", {'filename':filename}, actor_ref=self._saver_ref)
            m.tell("/serial/open", {'port':self.port, 'baudrate':self.baud, 'timeout':0.05}, actor_ref=self._ser_ref)
            self.openclose = "Close"
        else:
            # self._display_queue.append((close(), self._ser.channel))
            m.tell('/file_saver/stop_record')
            m.tell("/serial/close", actor_ref=self._ser_ref)
            self.openclose = "Open"
    
    def tell(self, message):
        topic = message.get('topic')
        if topic == '/data/display_data':
            data = message.get('data')
            self.recvtxt += data
            self.scroll.scroll_to(percent=1.0)
    
def myExit():
    ActorManager.singleton().stop_all()

app.on_shutdown(myExit)

if __name__ in {"__main__", "__mp_main__"}:
    logging.basicConfig(level=logging.DEBUG)
    signal.signal(signal.SIGUSR1, pykka.debug.log_thread_tracebacks)
    myUI = SerialUI()
    ui.run(native=True, reload=False)
