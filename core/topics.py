# Desc: topic constants
# 标准数据流
# /data/source --> /data/segment --> /data/convert --> /data/highlighten
# 原始数据，从source plugin发出的数据
#   数据格式：{'data':data, 'ts':时间戳, 'mode':模式（text， hex）}
TOPIC_RAW_DATA = '/data/source'

# 经过segment plugin处理后的数据, 
#   对于普通文本，只是简单的分割成行；对于二进制数据，按时间分行
#   也可以按照特定协议格式来分包
#   数据格式：{'data':data, 'ts':时间戳, mode:模式（text， hex）}
TOPIC_SEGMENT_DATA = '/data/segment'
#经过convert plugin处理后的数据
TOPIC_CONVERT_DATA = '/data/convert'
#将数据进行着色处理
TOPIC_HIGHLIGHTEN_DATA = '/data/highlighten'

