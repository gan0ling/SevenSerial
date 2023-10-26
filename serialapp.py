from collections import deque
import serial.tools.list_ports
from datetime import datetime
from core.manager import ActorManager
from core.coreplugin import SerialPlugin, SerialSegmentPlugin, Ansi2HtmlConverter, FileSaver
from core.sourceplugin import JLinkRttPlugin
from nicegui import ui, app
import logging

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
        self.port_list.append('JLink')
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
        self._vertical_percentage = 1.0
        self._jlink_ref = None
        self.jlink_target = None
        self.scroll_menu = "Scroll: Off"
        self._enable_scroll = True
        self._context_menu_open = False
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
                    ui.select(self.port_list, label="Port", on_change=self.onPortChange).bind_value(self, "port")
                    ui.select(self.baudrates, label="Baudrate").bind_value(self,"baud")
                    ui.button(on_click=self.onOpenClose).bind_text(self, "openclose")
                    ui.input().bind_value(self, "sendtxt")
                    ui.button(text="Send", on_click=self.onSend)
                ui.separator()
                # self._log = ui.log().classes("w-full").style("height: 84vh; overflow-y: scroll;")
                self.scroll = ui.scroll_area().classes("w-full").style("height: 84vh;")
                with self.scroll:
                    ui.html().bind_content(self, "recvtxt")
                    with ui.context_menu().on('show', self.onContextMenuShow).on('hide', self.onContextMenuHide):
                        ui.menu_item("Clear", on_click=self.onClear)
                        ui.menu_item("Scroll", on_click=self.onAutoScroll).bind_text(self, "scroll_menu")

    def onContextMenuShow(self):
        self._context_menu_open = True
    
    def onContextMenuHide(self):
        self._context_menu_open = False

    def onAutoScroll(self):
        #first disable scroll, 否则context_menu会跟随滚动
        self._enable_scroll = not self._enable_scroll
        if self._enable_scroll:
            self.scroll_menu = "Scroll: Off"
        else:
            self.scroll_menu = "Scroll: On"
    
    def onClear(self):
        self.recvtxt = ''
    
    def onPortChange(self, e):
        if e.value == "JLink":
            # 弹出窗口来选择JLink需要连接的设备
            with ui.dialog() as dialog, ui.card():
                ui.input(label="Target").bind_value(self, "jlink_target")
                ui.button(text="OK", on_click=dialog.close)
            dialog.open()


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
        if self.port == 'JLink':
            if not self._jlink_ref:
                self._jlink_ref = JLinkRttPlugin.start()
            if self.openclose == "Open":
                logging.debug("open jlink rtt")
                m.tell("/jlink_rtt/open", {'target':'EFR32BG22CxxxF512'})
                self.openclose = "Close"
            else:
                logging.debug("close jlink rtt")
                self.openclose = "Open"
                m.tell("/jlink_rtt/close")
            return
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
            if self._enable_scroll and not self._context_menu_open:
                self.scroll.scroll_to(percent=1.0)
    
def myExit():
    ActorManager.singleton().stop_all()

app.on_shutdown(myExit)

if __name__ in {"__main__", "__mp_main__"}:
    logging.basicConfig(level=logging.INFO)
    myUI = SerialUI()
    ui.run(native=True, reload=False)
