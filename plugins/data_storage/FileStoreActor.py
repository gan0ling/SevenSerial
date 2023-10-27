from core.plugintype import StorageActor 
import time

class FileStoreActor(StorageActor):
    """
        保存数据(DisplayData)到文件,
        文件格式：串口名_时间戳.log
    """
    def __init__(self): 
        super().__init__()
        self.f = None
        self._filename = None
        self._ts = time.time()
        self.topic_manager.subscribe('/cmd', self.actor_ref)
        self.topic_manager.subscribe('/display_data', self.actor_ref)
    
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
        self.f.flush()
    
    def on_receive(self, message):
        topic = message.get('topic')
        if topic == '/cmd' and 'cmd' in message:
            cmd = message.get('cmd')
            if cmd == 'open':
                self.on_StartRecord(message.get('filename'))
            elif cmd == 'close':
                self.on_StopRecord()
        elif topic == '/display_data':
            self.on_DisplayData(message.get('data'))
