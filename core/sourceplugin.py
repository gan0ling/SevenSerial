from typing import Any
from core.manager import ActorManager
from core.coreplugin import LoopActor
import pylink
import time
from datetime import datetime


class JLinkRttPlugin(LoopActor):
    def __init__(self, target=None):
        self._timeout = 0.5
        super().__init__(timeout=self._timeout, block=False)
        self._target = target
        self._jlink = None
        self.manager = ActorManager.singleton()
        self.manager.subscribe('/jlink_rtt/open', self.actor_ref)
        self.manager.subscribe('/jlink_rtt/close', self.actor_ref)
    
    def on_loop(self) -> None:
        if self._jlink : #and  self._jlink.connected():
            data = self._jlink.rtt_read(0, 1024)
            data = bytes(data).decode('utf-8', errors='ignore')
            now = datetime.now().strftime("%m-%d %H:%M:%S.%f")[:-3]
            if data:
                self.manager.tell('/data/raw', {'data':data, 'ts':now})
        else:
            time.sleep(self._timeout)
    
    def on_receive(self, message: Any) -> Any:
        topic = message['topic']
        if topic == '/jlink_rtt/open':
            self._target = message['target']
            if not self._jlink:
                self._jlink = pylink.JLink()
            self._jlink.open()
            self._jlink.set_tif(pylink.enums.JLinkInterfaces.SWD)
            self._jlink.connect(self._target)
            self._jlink.rtt_start()
        elif topic == '/jlink_rtt/close':
            if self._jlink and self._jlink.opened():
                self._jlink.rtt_stop()
                self._jlink.close()
                self._jlink = None
