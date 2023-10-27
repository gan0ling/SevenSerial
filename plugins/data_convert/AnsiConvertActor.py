from core.plugintype import ConvertActor
from stransi import Ansi, SetAttribute, SetColor

class Ansi2HtmlConverter(ConvertActor):
    """
    将Ansi转为html
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
        #TODO: 动态订阅数据Input的topic
        self.topic_manager.subscribe('/LineSegmentActor/output', self.actor_ref)
    
    def on_receive(self, message): 
        if message.get('topic') == '/LineSegmentActor/output':
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
        if mode == "hex":
            self.topic_manager.tell('/display_data', {'data':data, 'ts':ts, 'bg_color':self.bg_color, 'fg_color':self.fg_color})
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
        self.topic_manager.tell('/display_data', {'data':html, 'ts':ts, 'bg_color':self.bg_color, 'fg_color':self.fg_color})
