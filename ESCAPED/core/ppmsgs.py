from dataclasses import dataclass
from enum import Enum
from typing import Any

PPMsgType = Enum('PPMsgType',
              ['AliceMasked',
               'BobMasked',
               'Request'])


@dataclass
class PPMsg():
    msg_type : PPMsgType 


@dataclass
class AliceToBobMsg(PPMsg):
    masked_data : Any  
    partial_unmasker : Any 

@dataclass 
class BobToAliceMsg(PPMsg):
    masked_data : Any  

