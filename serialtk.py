import customtkinter
from tkinter import messagebox
import serial.tools.list_ports
from datetime import datetime
from core.manager import TopicManager, MyConfigurablePluginManager
from core.plugintype import ConvertActor, SourceActor, StorageActor, FilterActor, HighlightActor 
from configparser import ConfigParser
import queue, logging, copy
import sys,os
from stransi import Ansi, SetAttribute, SetColor

class MyAnsiTextBox(customtkinter.CTkTextbox):
    def __init__(self, master):
        super().__init__(master)
        #create tag according to ansi color
        self._color_names = ['black', 'red', 'green', 'yellow', 'blue', 'magenta', 'cyan', 'white']
        self.tag_config('fg_black', foreground='black')
        self.tag_config('fg_red', foreground='red')
        self.tag_config('fg_green', foreground='green')
        self.tag_config('fg_yellow', foreground='yellow')
        self.tag_config('fg_blue', foreground='blue')
        self.tag_config('fg_magenta', foreground='magenta')
        self.tag_config('fg_cyan', foreground='cyan')
        self.tag_config('fg_white', foreground='white')
        self.tag_config('bg_black', background='black')
        self.tag_config('bg_red', background='red')
        self.tag_config('bg_green', background='green')
        self.tag_config('bg_yellow', background='yellow')
        self.tag_config('bg_blue', background='blue')
        self.tag_config('bg_magenta', background='magenta')
        self.tag_config('bg_cyan', background='cyan')
        self.tag_config('bg_white', background='white')
        self.tag_config('default', foreground='black', background='white')
        # self.tag_config('bold', font=('Courier', 10, 'bold'))
        # self.tag_config('stroke', font=('Courier', 10, 'underline'))
        # self.tag_config('strong', font=('Courier', 10, 'bold'))
        # self.tag_config('normal', font=('Courier', 10, 'normal'))
        # self.tag_config('underline', underline=True)
        # self.bold = False
        # self.stroke = False
        # self.strong = False
        # self.underline = False
        self.fg_color = 'fg_white'
        self.bg_color = 'bg_black'
    
    def _cvtColor(self, color):
        return color.web_color.name
    
    def append_ansi(self, ansi_data):
        """
        将插入的数据按照ansi格式进行显示
        """
        for t in Ansi(ansi_data).instructions():
            if isinstance(t, str):
                tags = [self.fg_color, self.bg_color]
                # if self.bold:
                #     tags.append('bold')
                # if self.stroke:
                #     tags.append('stroke')
                # if self.strong:
                #     tags.append('strong')
                # if self.underline:
                #     tags.append('underline')
                # if not self.bold and not self.stroke and not self.strong:
                #     tags.append('normal')
                self.insert('end', t, tags)
                self.see('end')
            elif isinstance(t, SetAttribute):
                if t.attribute.name == "BOLD":
                    self.bold = True
                elif t.attribute.name == "STROKE":
                    self.stroke = True
                elif t.attribute.name == "STRONG":
                    self.strong = True
                elif t.attribute.name == "NORMAL":
                    self.bold = False
                    self.stroke = False
                    self.strong = False
                    self.fg_color = 'fg_black'
                    self.bg_color = 'bg_white'
            elif isinstance(t, SetColor):
                if t.role.name == "FOREGROUND":
                    if t.color:
                        self.fg_color = self._cvtColor(t.color)
                    else:
                        self.fg_color = 'fg_black'
                else:
                    if t.color:
                        self.bg_color = self._cvtColor(t.color)
                    else:
                        self.bg_color = 'bg_white'

class MyPortSelectWidget(customtkinter.CTkFrame):
    def __init__(self, master):
        super().__init__(master)
        ports = serial.tools.list_ports.comports()
        port_list = [p.device for p in ports]
        self.port_label = customtkinter.CTkLabel(self, text='Port:')
        self.port_label.grid(row=0, column=0, padx=10, pady=(10,0), sticky="w")

        self.port_value = customtkinter.StringVar()
        self.port_combo = customtkinter.CTkComboBox(self, values=port_list, variable=self.port_value)
        self.port_combo.grid(row=0, column=1, padx=10, pady=(10,0), sticky="ew")

        baud_list = [
            '300', '600', '1200', '2400', '4800', '9600', '14400', '19200', 
            '28800', '38400', '56000', '57600', '115200', '128000', '230400',
            '256000', '460800', '500000', '512000', '600000', '750000', '921600',
            '1000000', '1500000', '2000000', '2500000', '3000000', '3500000'
        ]
        self.baud_label = customtkinter.CTkLabel(self, text="Baud:")
        self.baud_label.grid(row=0, column=2, padx=10, pady=(10,0), sticky="w")

        self.baud_value = customtkinter.StringVar()
        self.baud_combo = customtkinter.CTkComboBox(self, values=baud_list, variable=self.baud_value)
        self.baud_combo.grid(row=0, column=3, padx=10, pady=(10,0), sticky="ew")

        self.grid_columnconfigure((1,3), weight=1)

    def fresh_port(self):
        ports = serial.tools.list_ports.comports()
        port_list = [p.device for p in ports]
        self.port_combo.configure(values=port_list)


    def get(self):
        """
        获取port和波特率
        """
        return (self.port_value.get(), self.baud_value.get())

class App(customtkinter.CTk):
    def __init__(self):
        super().__init__()
        self.protocol("WM_DELETE_WINDOW", self.on_exit)
        self._exit_loop = False
        self.logger = logging.getLogger("SerialApp")

        #setup ui
        self.title("SevenSerial")
        self.port_sel = MyPortSelectWidget(self)
        self.port_sel.grid(row=0, column=0, sticky="ew")
        self.open_close_btn = customtkinter.CTkButton(self, text="Open", command=self.on_open_close)
        self.open_close_btn.grid(row=0, column=1, padx=10, pady=(10,0), sticky="w")
        self.hex_mode_btn = customtkinter.CTkCheckBox(self, text="Hex", command=self.on_hex_mode)
        self.hex_mode_btn.grid(row=0, column=2, padx=10, pady=(10,0), sticky="w")

        self.display_widget = MyAnsiTextBox(self)
        self.display_widget.grid(row=1, column=0, padx=10, pady=(10,0), sticky="NSEW", columnspan=3)

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        #setup plugin
        self.msg_queue = queue.Queue()
        self.config_parser = ConfigParser()
        self.config_file = 'config.ini'
        self.config_parser.read(self.config_file)
        if getattr(sys, 'frozen', False):
            current_dir = sys._MEIPASS
        else:
            current_dir = os.path.dirname(os.path.abspath(__file__))

        path = os.path.join(current_dir, "plugins")
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
        m.subscribe('/LineSegmentActor/output', self)
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

    def tell(self, message):
        #deep copy message
        msg = copy.copy(message)
        self.logger.debug("tell: %s", msg)
        self.msg_queue.put(msg)

    def update_config(self):
        """
        Write the content of the ConfigParser in a file.
        """
        cf = open(self.config_file,"w")
        self.config_parser.write(cf)
        cf.close()

    def on_open_close(self):
        port,baud = self.port_sel.get()
        m = TopicManager.singleton()
        if port == 'JLink':
            plugin = self.plugin_manager.activatePluginByName('JLinkRttSourceActor', "Source", save_state=False)
            if self.open_close_btn.cget('text') == "Open":
                msg = {
                    'cmd': 'open',
                    'target': 'EFR32BG22CxxxF512',
                }
                m.tell('/cmd', msg, actor_ref=plugin.actor_ref)
                self.open_close_btn.configure(text="Close")
            else:
                self.logger.debug("close jlink rtt")
                self.open_close_btn.configure(text="Open")
                msg = {
                    'cmd': 'close'
                }
                m.tell('/cmd', msg, actor_ref=plugin.actor_ref)
            return
        self.plugin_manager.activatePluginByName('SerialSourceActor', "Source", save_state=False)
        if self.open_close_btn.cget('text') == "Open":
            #保存文件
            filename = "./log/" + port + "_" + datetime.now().strftime("%Y_%m_%d_%H_%M_%S") + ".html"
            msg = {
                'cmd': 'open',
                'filename': filename
            }
            m.tell('/cmd', msg, actor_ref=self.plugin_manager.getActorRefByName('FileStoreActor', "Storage"))
            ret = m.ask("/cmd", {'cmd':'open', 'port':port, 'baudrate':int(baud), 'timeout':0.05}, actor_ref=self.plugin_manager.getActorRefByName('SerialSourceActor', "Source"), timeout=1, block=True)
            if ret[0][1]:
                self.open_close_btn.configure(text="Close")
            else:
                messagebox.showerror("Error", "Open Serial Port Failed")
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
            self.open_close_btn.configure(text="Open")

    def on_hex_mode(self):
        print("hex mode") 

    def button_callback(self):
        print("button pressed")

    def on_exit(self):
        self._exit_loop = True
        TopicManager.singleton().stop_all()

    def mainloop(self, *args, **kwargs):
        while True:
            if self._exit_loop:
                self.destroy()
                break
            self.update()
            while self.msg_queue.qsize() > 0:
                msg = self.msg_queue.get(block=False)
                self.logger.debug("msg: %s", msg)
                if msg['topic'] == '/LineSegmentActor/output':
                    self.display_widget.append_ansi(msg['data'])

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    app = App()
    app.mainloop()
