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

    def on_cmd(self, msg):
        cmd = msg.get('cmd')
        if cmd == 'open':
            self.on_StartRecord(msg.get('filename'))
        elif cmd == 'close':
            self.on_StopRecord()

    def on_input(self, msg):
        self.on_DisplayData(msg.get('data')) 
