import serial
from pykka import ThreadingActor, Actor, ActorRegistry
import logging
import sys
import queue
from manager import ActorManager
from datetime import datetime
import time

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
        m = ActorManager.singleton()
        m.subscribe('/serial/open', self.actor_ref)
        m.subscribe('/serial/close', self.actor_ref)
        m.subscribe('/serial/write', self.actor_ref)
    
    def on_loop(self) -> None:
        if self.serial and self.serial.is_open and self.serial.in_waiting:
            data = self.serial.read(self.serial.in_waiting)
            #发布消息，topic为/serial/read data为data ts为当前时间戳
            print(data)
            m = ActorManager.singleton()
            now = datetime.now().strftime("%m-%d %H:%M:%S.%f")[:-3]
            m.tell('/serial/read', {'topic':'/serial/read', 'port':self.port,'data': data, 'ts': now})
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
        print("topic: ", topic)
        if topic == '/serial/open':
            self.on_open(message)
        elif topic == '/serial/close':
            self.on_close(message)
        elif topic == '/serial/write':
            self.on_write(message)
