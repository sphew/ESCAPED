from dataclasses import dataclass
from enum import Enum
from typing import Any


MsgType = Enum('MsgType',
                  ['OwnGram',
                   'AliceGram',
                   'BobGram',
                   'Label',
                   'UserDef'])

ReqType = Enum('ReqType',
                  ['YourGram',
                   'NextPeerGram',
                   'Label',
                   'UserDef',
                   'Teardown'])

@dataclass 
class PeerGram():
    pairing_id : (str, str)
    component : Any 
    unmasker : Any 



@dataclass
class PFMsg():
    request_id : int = 0

@dataclass
class PFRequestMsg(PFMsg):
    req_type: ReqType = None
    spec: Any = None

@dataclass
class PFDataMsg(PFMsg):
    msg_type: MsgType = None
    data: PeerGram | Any = None 






