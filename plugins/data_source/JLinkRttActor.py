from typing import Any
import pylink
import time
from datetime import datetime
from core.plugintype import SourceActor

class JLinkRttSourceActor(SourceActor):
    def __init__(self, target=None):
        self._timeout = 0.5
        super().__init__(timeout=self._timeout, block=False)
        self._target = target
        self._jlink = None
        self.topic_manager.subscribe('/cmd', self.actor_ref)
    
    def on_poll(self) -> None:
        if self._jlink : #and  self._jlink.connected():
            data = self._jlink.rtt_read(0, 1024)
            data = bytes(data).decode('utf-8', errors='ignore')
            now = datetime.now().strftime("%m-%d %H:%M:%S.%f")[:-3]
            if data:
                self.topic_manager.tell('/JLinkRttSourceActor/output', {'data':data, 'ts':now})
        else:
            time.sleep(self._timeout)
    
    def on_receive(self, message: Any) -> Any:
        topic = message['topic']
        if topic == '/cmd' and 'cmd' in message:
            cmd = message['cmd']
            if cmd == 'open':
                self._target = message['target']
                if not self._jlink:
                    self._jlink = pylink.JLink()
                self._jlink.open()
                self._jlink.set_tif(pylink.enums.JLinkInterfaces.SWD)
                self._jlink.connect(self._target)
                self._jlink.rtt_start()
            elif cmd == 'close':
                if self._jlink and self._jlink.opened():
                    self._jlink.rtt_stop()
                    self._jlink.close()
                    self._jlink = None

