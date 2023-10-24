from typing import Any
import serial
from pykka import ThreadingActor, Actor, ActorRegistry
import logging
import sys
import queue
from manager import ActorManager
from datetime import datetime
import time
from stransi import Ansi, SetColor, SetAttribute

logger = logging.getLogger("pykka")
class LoopActor(ThreadingActor):
    def __init__(self, timeout=0.05, block=True):
        super().__init__()
        self.timeout = timeout
        self.block = block
    
    def on_loop(self) -> None:
        """
        Called on every loop iteration.
        """
        raise NotImplementedError

    def _actor_loop_running(self) -> None:
        while not self.actor_stopped.is_set():
            if not self.block:
                self.on_loop()
            try:
                envelope = self.actor_inbox.get(timeout=self.timeout, block=self.block)
            except queue.Empty:
                continue
            try:
                response = self._handle_receive(envelope.message)
                if envelope.reply_to is not None:
                    envelope.reply_to.set(response)
            except Exception:
                if envelope.reply_to is not None:
                    logger.info(
                        f"Exception returned from {self} to caller:",
                        exc_info=sys.exc_info(),
                    )
                    envelope.reply_to.set_exception()
                else:
                    self._handle_failure(*sys.exc_info())
                    try:
                        self.on_failure(*sys.exc_info())
                    except Exception:
                        self._handle_failure(*sys.exc_info())
            except BaseException:
                exception_value = sys.exc_info()[1]
                logger.debug(f"{exception_value!r} in {self}. Stopping all actors.")
                self._stop()
                ActorRegistry.stop_all()



class SerialPlugin(LoopActor):
    def __init__(self, port=None, baudrate=115200):
        super().__init__(timeout=0.05, block=False)
        self.port = port 
        self.baudrate = 115200
        self.serial = None
        self.manager = ActorManager.singleton()
        self.manager.subscribe('/serial/open', self.actor_ref)
        self.manager.subscribe('/serial/close', self.actor_ref)
        self.manager.subscribe('/serial/write', self.actor_ref)

    def on_stop(self) -> None:
        super().on_stop() 
    
    def on_loop(self) -> None:
        if self.serial and self.serial.is_open and self.serial.in_waiting:
            data = self.serial.read(self.serial.in_waiting).decode('utf-8', errors='ignore')
            #发布消息，topic为/serial/read data为data ts为当前时间戳
            now = datetime.now().strftime("%m-%d %H:%M:%S.%f")[:-3]
            self.manager.tell('/data/raw', {'topic':'/data/raw', 'port':self.port,'data': data, 'ts': now})
        else:
            time.sleep(self.timeout)

    def on_open(self, message):
        """
        打开串口, 若之前已经打开，则先关闭
            message: 字典
                topic: 字符串
                port: 字符串
                baudrate: 波特率
                timeout: float
        """
        if self.serial and self.serial.is_open:
            self.serial.close()
            self.serial = None
        self.port = message.get('port')
        self.baudrate = message.get('baudrate')
        self.timeout = message.get('timeout', self.timeout)
        self.serial = serial.Serial(self.port, self.baudrate, timeout=self.timeout)
        # self.serial.open()

    def on_close(self, message):
        if self.serial and self.serial.is_open:
            self.serial.close()
        self.serial = None

    def on_write(self, message):
        if self.serial and self.serial.is_open:
            data = message.get('data')
            self.serial.write(data)

    def on_receive(self, message):
        topic = message.get('topic')
        if topic == '/serial/open':
            self.on_open(message)
        elif topic == '/serial/close':
            self.on_close(message)
        elif topic == '/serial/write':
            self.on_write(message)

class SerialSegmentPlugin(ThreadingActor):
    """
    将数据分段：
    1. 文本模式下，按照行来分段，并且增加时间戳
    2. Hex模式下， 按照时间来分段, 默认50ms
    Output Topic：
        /data/segment_data
    Input Topic:
        /data/set_segment_mode: 设置分段模式
        /data/raw: 读数据
    """
    def __init__(self, mode="text"):
        super().__init__()
        self._mode = mode
        self._last_hex_time = None
        #订阅消息
        m = ActorManager.singleton()
        m.subscribe('/data/raw', self.actor_ref)
        m.subscribe('/data/set_segment_mode', self.actor_ref)
    
    def on_stop(self) -> None:
        super().on_stop()
    
    def on_receive(self, message: Any) -> Any:
        topic = message.get('topic')
        if topic == '/data/raw':
            self.on_data(message.get('data'), message.get('ts'))
        elif topic == '/data/set_segment_mode':
            self._mode = message.get('mode')
    
    def on_data(self, data, ts):
        m = ActorManager.singleton()
        if self._mode == "text":
            #文本模式
            for line in data.splitlines(keepends=True):
                #为每行数据增加时间戳
                line = "[" + ts + "] " + line
                m.tell('/data/segment_data', {'data':line, 'ts':ts, 'mode':'text'})

        else :
            #HEX模式,将数据转为hex string
            #每隔50ms分段
            #TODO: 使用component来实现Hex数据的分段
            if self._last_hex_time:
                datetime.now() - self._last_hex_time > 0.05
                m.tell('/data/segment_data', {'data':'\n'+ts, 'ts':ts, 'mode':'hex'})
            data = data.hex()
            m.tell('/data/segment_data', {'data':data, 'ts':ts, 'mode':'hex'})
            self._last_hex_time = datetime.now()
    

class Ansi2HtmlConverter(ThreadingActor):
    """
    将Ansi转为html
    Topic：
        input：
            /data/segment_data
        output:
            /data/display_data
    """
    def __init__(self, fg_color="black", bg_color="white"):
        super().__init__()
        self.bg_color = bg_color
        self.fg_color = fg_color
        self.default_bg_color = bg_color
        self.default_fg_color = fg_color
        self.bold = False
        self.stroke = False
        self.strong = False
        m = ActorManager.singleton()
        m.subscribe('/data/segment_data', self.actor_ref)
    
    def on_receive(self, message: Any) -> Any:
        if message.get('topic') == '/data/segment_data':
            self.on_SegmentData(message.get('data'), message.get('ts'), message.get('mode'))

    def SetColor(self, bg_color, fg_color):
        self.bg_color = bg_color
        self.fg_color = fg_color
    def SetDefaultColor(self, bg_color, fg_color):
        self.default_bg_color = bg_color
        self.default_fg_color = fg_color
    
    def _cvtColor(self, color):
        # return "#{:x}".format(color) 
        return color.web_color.name
    
    def on_SegmentData(self, data, ts, mode):
        m = ActorManager.singleton()
        if mode == "hex":
            m.tell('/data/display_data', {'data':data, 'ts':ts, 'bg_color':self.bg_color, 'fg_color':self.fg_color})
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
        m.tell('/data/display_data', {'data':html, 'ts':ts, 'bg_color':self.bg_color, 'fg_color':self.fg_color})

class FileSaver(ThreadingActor):
    """
        保存数据(DisplayData)到文件,
        文件格式：串口名_时间戳.log
        Topic:
            input:
                /file_saver/start_record : {"filename":filename}
                /file_saver/stop_record : None
                /data/display_data
            output:
                None
    """
    def __init__(self, channel="serial"):
        super().__init__()
        self.f = None
        self._filename = None
        m = ActorManager.singleton()
        m.subscribe('/file_saver/start_record', self.actor_ref)
        m.subscribe('/file_saver/stop_record', self.actor_ref)
        m.subscribe('/data/display_data', self.actor_ref)
    
    def on_StartRecord(self, filename):
        if not filename:
            return   
        if self.f is not None:
            self.f.close()
        self._filename = filename
        self.f = open(filename, "w", encoding="utf-8")
    
    def on_StopRecord(self):
        if self.f is not None:
            self.f.close()
            self.f = None
            self._filename = None
    
    def on_DisplayData(self, data):
        if self.f is None:
            return
        self.f.write(data)
    
    def on_receive(self, message: Any) -> Any:
        topic = message.get('topic')
        if topic == '/file_saver/start_record':
            self.on_StartRecord(message.get('filename'))
        elif topic == '/file_saver/stop_record':
            self.on_StopRecord()
        elif topic == '/data/display_data':
            self.on_DisplayData(message.get('data'))
