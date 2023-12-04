import serial.tools.list_ports
from datetime import datetime
from core.manager import TopicManager, MyConfigurablePluginManager
from core.plugintype import ConvertActor, SourceActor, StorageActor, FilterActor, HighlightActor 
from configparser import ConfigParser
import queue, logging, copy
import sys,os
from PySide6.QtWidgets import QApplication, QMainWindow, QMessageBox
from PySide6.QtCore import Slot, QTimer
from ui.ui_main import Ui_MainWindow


class SerialApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)
        self.logger = logging.getLogger('SerialApp')
        self.port_list = None 
        self.baudrates = [
            300, 600, 1200, 2400, 4800, 9600, 14400, 19200, 
            28800, 38400, 56000, 57600, 115200, 128000, 230400,
            256000, 460800, 500000, 512000, 600000, 750000, 921600,
            1000000, 1500000, 2000000, 2500000, 3000000, 3500000
        ]
        self.ui.comboBox_baud.addItems([str(b) for b in self.baudrates])
        self.baud = 115200
        self.ui.comboBox_baud.setCurrentText(str(self.baud))
        self.freshport()
        self.ui.comboBox_port.addItems([p for p in self.port_list])
        self.port = self.port_list[0] or None
        if self.port:
            self.ui.comboBox_port.setCurrentText(self.port)
        self.sendtxt = ""
        self.recvtxt = ""
        #setup plugin
        self.msg_queue = queue.Queue()
        self.config_parser = ConfigParser()
        self.config_file = 'config.ini'
        self.config_parser.read(self.config_file)
        if getattr(sys, 'frozen', False):
            current_dir = sys._MEIPASS
        else:
            current_dir = os.path.dirname(os.path.abspath(__file__))

        print("current_dir:", current_dir)
        path = os.path.join(current_dir, "plugins")
        print("path:", path)
        self.plugin_manager = MyConfigurablePluginManager(
            configparser_instance=self.config_parser,
            categories_filter={
                "Source": SourceActor,
                "Filter": FilterActor,
                "Convert": ConvertActor,
                "Highlight": HighlightActor,
                "Storage": StorageActor,
            },
            directories_list=[path],
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
        #注册timer
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.backgound_task)
        self.timer.start(20)

    def freshport(self):
        ports = serial.tools.list_ports.comports()
        self.port_list = [p.device for p in ports]

    def tell(self, message):
        #deep copy message
        msg = copy.copy(message)
        self.logger.debug("tell: %s", msg)
        self.msg_queue.put(msg)
    
    def backgound_task(self):
        while self.msg_queue.qsize() > 0:
            msg = self.msg_queue.get(block=False)
            self.logger.debug("msg: %s", msg)
            if msg['topic'] == '/Ansi2HtmlConverter/output':
                # self.recvtxt += msg['data']
                self.ui.textEdit.insertHtml(msg['data'])
                #scroll to bottom
                self.ui.textEdit.verticalScrollBar().setValue(self.ui.textEdit.verticalScrollBar().maximum())

    @Slot(str)
    def on_comboBox_port_currentTextChanged(self, text):
        self.port = self.ui.comboBox_port.currentText()

    @Slot(str)
    def on_comboBox_baud_currentTextChanged(self, text):
        self.baud = int(self.ui.comboBox_baud.currentText())
    
    @Slot()
    def on_btn_openclose_clicked(self):
        m = TopicManager.singleton()
        if self.port == 'JLink':
            plugin = self.plugin_manager.activatePluginByName('JLinkRttSourceActor', "Source", save_state=False)
            if self.ui.btn_openclose.text() == "Open":
                msg = {
                    'cmd': 'open',
                    'target': 'EFR32BG22CxxxF512',
                }
                m.tell('/cmd', msg, actor_ref=plugin.actor_ref)
                self.ui.btn_openclose.setText("Close")
            else:
                self.logger.debug("close jlink rtt")
                self.ui.btn_openclose.setText("Open")
                msg = {
                    'cmd': 'close'
                }
                m.tell('/cmd', msg, actor_ref=plugin.actor_ref)
            return
        self.plugin_manager.activatePluginByName('SerialSourceActor', "Source", save_state=False)
        if self.ui.btn_openclose.text() == "Open":
            #保存文件
            filename = "./log/" + self.port + "_" + datetime.now().strftime("%Y_%m_%d_%H_%M_%S") + ".html"
            msg = {
                'cmd': 'open',
                'filename': filename
            }
            m.tell('/cmd', msg, actor_ref=self.plugin_manager.getActorRefByName('FileStoreActor', "Storage"))
            ret = m.ask("/cmd", {'cmd':'open', 'port':self.port, 'baudrate':self.baud, 'timeout':0.05}, actor_ref=self.plugin_manager.getActorRefByName('SerialSourceActor', "Source"), timeout=1, block=True)
            if ret[0][1]:
                self.ui.btn_openclose.setText("Close")
            else:
                # ui.notify("Open Serial Port Failed", type="error")
                QMessageBox.critical(self, "Error", "Open Serial Port Failed") 
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
            self.ui.btn_openclose.setText("Open")

    def onSend(self, widget):
        print("onSend")
    
    def update_config(self):
        """
        Write the content of the ConfigParser in a file.
        """
        cf = open(self.config_file,"w")
        self.config_parser.write(cf)
        cf.close()
    
def onExit():
    TopicManager.singleton().stop_all()

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    app = QApplication(sys.argv)
    app.aboutToQuit.connect(onExit)
    win = SerialApp()
    win.show()
    sys.exit(app.exec())
