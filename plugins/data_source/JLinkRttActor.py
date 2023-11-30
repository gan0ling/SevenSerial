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
    
    def on_poll(self) -> None:
        if self._jlink : #and  self._jlink.connected():
            data = self._jlink.rtt_read(0, 1024)
            data = bytes(data).decode('utf-8', errors='ignore')
            now = datetime.now().strftime("%m-%d %H:%M:%S.%f")[:-3]
            if data:
                self.tell({'data':data, 'ts':now})
        else:
            time.sleep(self._timeout)
    
    def on_cmd(self, msg):
        if 'cmd' not in msg:
            return
        cmd = msg['cmd']
        if cmd == 'open':
            self._target = msg['target']
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

