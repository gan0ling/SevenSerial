import re
from core.plugintype import ConvertActor
from dataclasses import dataclass

@dataclass
class Word:
    ts_str: str
    ts: int
    word: str 
    val:[]

class TextWordConvert(ConvertActor):
    def __init__(self):
        super().__init__()
    
    def on_input(self, msg):
        if 'data' in msg and 'ts' in msg:
            self.process_line(msg.get('data'), msg.get('ts'))
    
    def on_cmd(self, msg):
        pass
    
    def process_line(self, line, ts):
        #将一行文本分解为单词
        #单词可以用空格，逗号，分号分隔

