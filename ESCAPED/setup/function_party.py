import numpy as np 
import logging
from collections import deque
import socket
import struct
import pickle

from ESCAPED.core.escaped_function_party import ESCAPEDFunctionParty

class FP(ESCAPEDFunctionParty):

    TIMEOUT_THRESHOLD = 10 
    CHUNK_LEN = 4096 
    MAILBOX_SIZE = 10 
    RCV_REQUEST = bytearray(4) 

    def __init__(self, connector_addr):

        self._input_buf = deque()
        self._addrs = self._rcv(connector_addr)
        self.peers = [p for p in self._addrs.keys() if p != self.FP_ID]

    def _encode(self, msg):
        emsg = pickle.dumps((self.FP_ID, msg))
        return struct.pack('!I', len(emsg)) + emsg

    def _decode(self, msg):
        return pickle.loads(msg)


    def get_next_msg(self):
        self._check_mailbox()
        return self._input_buf.popleft()

    def add_to_msg_queue(self, msg):
        self._check_mailbox()
        self._input_buf.append((self.FP_ID, msg))

    def queue_empty(self):
        return not bool(self._input_buf) 

    def send_to_peer(self, req, peer):
        addr = self._addrs[peer]
        emsg = self._encode(req)
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.connect(addr)
            sock.sendall(emsg)

    def _check_mailbox(self):
        addr = self._addrs[self.FP_ID]
        for _ in range(self.MAILBOX_SIZE):
            mail = self._rcv(addr)
            if mail:
                self._input_buf.append(mail)
            else:
                break

    def _rcv(self, addr):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
             sock.connect(addr)
             sock.sendall(self.RCV_REQUEST)
             hdr = sock.recv(4)
             conlen = struct.unpack('!I', hdr)[0]
             if conlen:
                 rcvlen = 0
                 chunks = []
                 while rcvlen < conlen:
                     chunk = sock.recv(self.CHUNK_LEN) 
                     chunks.append(chunk)
                     rcvlen += len(chunk)
                     if not chunk:
                         logging.warning("[instFP] Something went wrong while receiving a msg.") 
                         return None
                 data = b''.join(chunks)
                 try :
                     msg = self._decode(data[:conlen])
                     return msg
                 except:
                     logging.error("[instFP] cannot decode this message of length %s. Will do nothing.", len(data))
             else:
                 return None

