"""Bounded JSON frames over private anonymous pipes, never pickle or file paths."""
import json,struct
MAX_FRAME=36*1024*1024
def read_exact(stream,size):
    result=bytearray()
    while len(result)<size:
        chunk=stream.read(size-len(result))
        if not chunk:raise EOFError('Worker pipe closed.')
        result.extend(chunk)
    return bytes(result)
def read_frame(stream):
    size=struct.unpack('!I',read_exact(stream,4))[0]
    if not 0<size<=MAX_FRAME:raise ValueError('Invalid worker frame size.')
    value=json.loads(read_exact(stream,size))
    if not isinstance(value,dict):raise ValueError('Worker message must be an object.')
    return value
def write_frame(stream,value):
    data=json.dumps(value,allow_nan=False,separators=(',',':')).encode()
    if not 0<len(data)<=MAX_FRAME:raise ValueError('Worker message too large.')
    stream.write(struct.pack('!I',len(data))+data);stream.flush()
