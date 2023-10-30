import serial.tools.list_ports
from datetime import datetime
from core.manager import TopicManager, MyConfigurablePluginManager
from nicegui import ui, app
import logging
from core.plugintype import ConvertActor, SourceActor, StorageActor, FilterActor, HighlightActor 
from configparser import ConfigParser

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
        self.config_parser = ConfigParser()
        self.config_file = 'app.ini'
        self.config_parser.read(self.config_file)
        self.plugin_manager = MyConfigurablePluginManager(
            configparser_instance=self.config_parser,
            categories_filter={
                "Source": SourceActor,
                "Filter": FilterActor,
                "Convert": ConvertActor,
                "Highlight": HighlightActor,
                "Storage": StorageActor,
            },
            directories_list=["plugins"],
            plugin_info_ext="ini",
            config_change_trigger=self.update_config
        )
        self.plugin_manager.collectPlugins()

        m = TopicManager.singleton()
        m.subscribe('/Ansi2HtmlConverter/output', self)
        #将各个actor的topic串联起来
        #SerialSource/output -> LineSegment/input, LineSegment/output -> AnsiConvert/input, AnsiConvert/output -> FileStore/input
        m.connect(self.plugin_manager.getActorByName('SerialSourceActor', "Source"), self.plugin_manager.getActorByName('LineSegmentActor', "Convert"))
        m.connect(self.plugin_manager.getActorByName('LineSegmentActor', "Convert"), self.plugin_manager.getActorByName('Ansi2HtmlConverter', "Convert"))
        m.connect(self.plugin_manager.getActorByName('Ansi2HtmlConverter', "Convert"), self.plugin_manager.getActorByName('FileStoreActor', "Storage"))
        m.connect(self.plugin_manager.getActorByName('JLinkRttSourceActor', "Source"), self.plugin_manager.getActorByName('LineSegmentActor', "Convert"))


        self.jlink_target = None
        self.scroll_menu = "Scroll: Off"
        self._enable_scroll = True
        self._context_menu_open = False
        #setup ui
        ui.keyboard(on_key=self.onKey)
        self.topTabs = ui.tabs().classes('w-full')
        self.tabs = []
        with self.topTabs:
            self.tabs.append(ui.tab('Serial-0'))
        self.panels = ui.tab_panels(self.topTabs, value=self.tabs[0]).classes('w-full')
        with self.panels:
            with ui.tab_panel(self.tabs[0]):
                with ui.row().classes("w-full q-pa-sm"):
                    #menu
                    # self.menu = ui.menu()
                    with ui.button(icon='menu'):
                        with ui.menu() as master_menu:
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
                self.scroll = ui.scroll_area().classes("w-full").style("height: 76vh;")
                with self.scroll:
                    ui.html().bind_content(self, "recvtxt")
                    with ui.context_menu().on('show', self.onContextMenuShow).on('hide', self.onContextMenuHide) as context_menu:
                        ui.menu_item("Clear", on_click=self.onClear)
                        ui.menu_item("Scroll", on_click=self.onAutoScroll).bind_text(self, "scroll_menu")
    
    def onKey(self, e):
        if not e.action.keydown:
            return
        if e.key == 'f' and (e.modifiers.ctrl or e.modifiers.meta):
            print("ctrl+f")

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
        m = TopicManager.singleton()
        if self.port == 'JLink':
            plugin = self.plugin_manager._component.getPluginByName('JLinkRttSourceActor', "Source")
        else:
            plugin = self.plugin_manager._component.getPluginByName('SerialSourceActor', "Source")
        m.tell("/write", {'data':self.sendtxt}, actor_ref=plugin.plugin_object.actor_ref)

    def onOpenClose(self, e):
        m = TopicManager.singleton()
        self.plugin_manager.activatePluginByName('LineSegmentActor', "Convert", save_state=False)
        self.plugin_manager.activatePluginByName('FileStoreActor', "Storage", save_state=False)
        self.plugin_manager.activatePluginByName('Ansi2HtmlConverter', "Convert", save_state=False)
        if self.port == 'JLink':
            plugin = self.plugin_manager.activatePluginByName('JLinkRttSourceActor', "Source", save_state=False)
            if self.openclose == "Open":
                msg = {
                    'cmd': 'open',
                    'target': 'EFR32BG22CxxxF512',
                }
                m.tell('/cmd', msg, actor_ref=plugin.plugin_object.actor_ref)
                self.openclose = "Close"
            else:
                logging.debug("close jlink rtt")
                self.openclose = "Open"
                msg = {
                    'cmd': 'close'
                }
                m.tell('/cmd', msg, actor_ref=plugin.plugin_object.actor_ref)
            return
        self.plugin_manager.activatePluginByName('SerialSourceActor', "Source", save_state=False)
        if self.openclose == "Open":
            #保存文件
            filename = "./log/" + self.port + "_" + datetime.now().strftime("%Y_%m_%d_%H_%M_%S") + ".html"
            msg = {
                'cmd': 'open',
                'filename': filename
            }
            m.tell('/cmd', msg, actor_ref=self.plugin_manager.getActorRefByName('FileStoreActor', "Storage"))
            ret = m.ask("/cmd", {'cmd':'open', 'port':self.port, 'baudrate':self.baud, 'timeout':0.05}, actor_ref=self.plugin_manager.getActorRefByName('SerialSourceActor', "Source"), timeout=1, block=True)
            if ret[0][1]:
                self.openclose = "Close"
            else:
                ui.notify("Open Serial Port Failed", type="error")
        else:
            # self._display_queue.append((close(), self._ser.channel))
            msg = {
                'cmd': 'close'
            }
            actors = [
                self.plugin_manager.getActorRefByName('SerialSourceActor', "Source"),
                self.plugin_manager.getActorRefByName('FileStoreActor', "Storage"),
            ]
            m.tell('/cmd', msg, actor_ref=actors)
            self.openclose = "Open"
    
    def tell(self, message):
        data = message.get('data')
        self.recvtxt += data
        if self._enable_scroll and not self._context_menu_open:
            self.scroll.scroll_to(percent=1.0)
    
    def update_config(self):
        """
        Write the content of the ConfigParser in a file.
        """
        cf = open(self.config_file,"w")
        self.config_parser.write(cf)
        cf.close()
    
def myExit():
    TopicManager.singleton().stop_all()

app.on_shutdown(myExit)
app.on_disconnect(myExit)

logging.basicConfig(level=logging.INFO)
myUI = SerialUI()
ui.run(native=True, reload=False)
