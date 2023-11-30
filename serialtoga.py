import toga
from toga.constants import COLUMN, ROW
from toga.style import Pack
import serial.tools.list_ports
from datetime import datetime
from core.manager import TopicManager, MyConfigurablePluginManager
from core.plugintype import ConvertActor, SourceActor, StorageActor, FilterActor, HighlightActor 
from configparser import ConfigParser
import queue
import asyncio
import logging
import copy

class SerialApp(toga.App):
    def freshport(self):
        ports = serial.tools.list_ports.comports()
        self.port_list = [p.device for p in ports]

    def startup(self):
        self.logger = logging.getLogger('SerialApp')
        self.main_window = toga.MainWindow()
        self.on_exit = self.onExit
        self.main_window.content = toga.Box(style=Pack(direction=COLUMN))
        self.port_list = None 
        self.baudrates = [
            300, 600, 1200, 2400, 4800, 9600, 14400, 19200, 
            28800, 38400, 56000, 57600, 115200, 128000, 230400,
            256000, 460800, 500000, 512000, 600000, 750000, 921600,
            1000000, 1500000, 2000000, 2500000, 3000000, 3500000
        ]
        self.freshport()
        self.port = self.port_list[0] or None
        self.baud = 115200
        self.sendtxt = ""
        self.recvtxt = ""
        self.ui_port_list = toga.Selection(items=self.port_list, on_change=self.onPortChange, value=self.port)
        self.ui_baud_list = toga.Selection(items=self.baudrates, value=self.baud, on_change=self.onBaudChange)
        self.ui_main_dispaly = toga.MultilineTextInput(style=Pack(flex=1))
        self.ui_status_bar = toga.Label('status:')
        self.ui_openclose_btn = toga.Button("Open", on_press=self.onOpenClose)
        #setup ui
        # self.main_window.content.add(
        #     toga.Box(
        #         children=[self.ui_main_dispaly],
        #         style=Pack(direction=COLUMN, flex=1)
        #     )
        # )
        self.main_window.content.add(self.ui_main_dispaly)
        self.main_window.content.add(
            toga.Box(
                children=[
                    toga.Label("Port"),
                    self.ui_port_list,
                    toga.Label("Baudrate"),
                    self.ui_baud_list,
                    self.ui_openclose_btn
                ],
                style=Pack(direction=ROW)
            )
        )
        self.main_window.content.add(self.ui_status_bar)
        self.main_window.show()
        #setup plugin
        self.msg_queue = queue.Queue()
        self.config_parser = ConfigParser()
        self.config_file = 'config.ini'
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
        #activate plugin
        self.plugin_manager.activatePluginByName('LineSegmentActor', "Convert", save_state=False)
        self.plugin_manager.activatePluginByName('FileStoreActor', "Storage", save_state=False)
        self.plugin_manager.activatePluginByName('Ansi2HtmlConverter', "Convert", save_state=False)
        #add background task
        self.add_background_task(self.backgound_task)

    def tell(self, message):
        #deep copy message
        msg = copy.deepcopy(message)
        self.logger.debug("tell: %s", msg)
        self.msg_queue.put(msg)
    
    async def backgound_task(self, widget):
        while True:
            while self.msg_queue.qsize() > 0:
                msg = self.msg_queue.get(block=False)
                self.logger.debug("msg: %s", msg)
                if msg['topic'] == '/Ansi2HtmlConverter/output':
                    self.logger.debug('add to display')
                    self.ui_main_dispaly.value += msg['data']
            await asyncio.sleep(0.02)

    def onPortChange(self, widget):
        self.port = self.ui_port_list.value
    def onBaudChange(self, widget):
        self.baud = self.ui_baud_list.value
    
    def onOpenClose(self, widget):
        m = TopicManager.singleton()
        if self.ui_port_list.value == 'JLink':
            plugin = self.plugin_manager.activatePluginByName('JLinkRttSourceActor', "Source", save_state=False)
            if self.ui_openclose_btn.text == "Open":
                msg = {
                    'cmd': 'open',
                    'target': 'EFR32BG22CxxxF512',
                }
                m.tell('/cmd', msg, actor_ref=plugin.actor_ref)
                self.ui_openclose_btn.text = "Close"
            else:
                self.logger.debug("close jlink rtt")
                self.ui_openclose_btn.text = "Open"
                msg = {
                    'cmd': 'close'
                }
                m.tell('/cmd', msg, actor_ref=plugin.actor_ref)
            return
        self.plugin_manager.activatePluginByName('SerialSourceActor', "Source", save_state=False)
        if self.ui_openclose_btn.text == "Open":
            #保存文件
            filename = "./log/" + self.port + "_" + datetime.now().strftime("%Y_%m_%d_%H_%M_%S") + ".html"
            msg = {
                'cmd': 'open',
                'filename': filename
            }
            m.tell('/cmd', msg, actor_ref=self.plugin_manager.getActorRefByName('FileStoreActor', "Storage"))
            ret = m.ask("/cmd", {'cmd':'open', 'port':self.port, 'baudrate':self.baud, 'timeout':0.05}, actor_ref=self.plugin_manager.getActorRefByName('SerialSourceActor', "Source"), timeout=1, block=True)
            if ret[0][1]:
                self.ui_openclose_btn.text = "Close"
            else:
                # ui.notify("Open Serial Port Failed", type="error")
                self.main_window.error_dialog("Open Serial Port Failed")
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
            self.ui_openclose_btn.text = "Open"

    def onSend(self, widget):
        print("onSend")
    
    def update_config(self):
        """
        Write the content of the ConfigParser in a file.
        """
        cf = open(self.config_file,"w")
        self.config_parser.write(cf)
        cf.close()
    
    def onExit(self, app):
        TopicManager.singleton().stop_all()
        return True

if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG)
    app = SerialApp('7Serial', 'org.beeware.7serial')
    app.main_loop()
