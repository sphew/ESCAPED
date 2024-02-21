import numpy as np 
import pandas as pd
import logging
from collections import deque
import socket
import struct
import pickle

from ESCAPED.core.escaped_peer import ESCAPEDPeer, PPRole

class Peer(ESCAPEDPeer):
    
    RAND_MIN = 1 
    RAND_MAX = 42 
    TIMEOUT_THRESHOLD = 1 

    RCV_REQUEST = bytearray(4)
    CHUNK_LEN = 4096
    MAILBOX_SIZE = 10


    def __init__(self, name, connector_addr, data):

        self.own_peer_id = name
        
        # initialization
        self._addrs = self._rcv(connector_addr)

        self.peers = [p for p in list(self._addrs.keys()) if p != self.FP_ID and p != self.own_peer_id] 

        self._roles = {peer : PPRole.Alice if self.own_peer_id < peer else PPRole.Bob for peer in self.peers} 


        # message buffer
        self._input_buf = deque()

        self._data = data 

    @classmethod
    def fromfile(cls, name, connector_addr, path_to_data_csv, startrow=0, nbrows=None):
        data = pd.read_csv(path_to_data_csv, sep=',', header=None, index_col=False,  skiprows=startrow, nrows=nbrows) 
        return cls(name, connector_addr, data) 


    def _rcv(self, addr):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.connect(addr)
            sock.sendall(self.RCV_REQUEST)
            hdr = sock.recv(4)
            conlen = struct.unpack("!I", hdr)[0]
            if conlen:
                rcvlen = 0
                chunks = []
                while rcvlen < conlen:
                    chunk = sock.recv(self.CHUNK_LEN)
                    chunks.append(chunk)
                    rcvlen += len(chunk) 
                    if not chunk:
                        logging.warning("[instPeer] %s: Something went wrong while receiving a msg.", self.own_peer_id)
                        return None
                data = b''.join(chunks)
                try :
                    msg = self._decode(data[:conlen])
                    return msg
                except:
                    logging.error("[instPeer] cannot decode this message. Will do nothing.")
            else: #no message available
                return None

    def _encode(self, msg):
        emsg = pickle.dumps((self.own_peer_id , msg))
        msghdr = struct.pack("!I", len(emsg))
        return msghdr + emsg


    def _decode(self, msg):
        return pickle.loads(msg)


    def get_next_msg(self):
        self._check_mailbox()
        if self._input_buf:
            return self._input_buf.popleft()
        else:
            return None, None


    def _check_mailbox(self):
        addr = self._addrs[self.own_peer_id]
        for _ in range(self.MAILBOX_SIZE):
            mail = self._rcv(addr)
            if mail:
                self._input_buf.append(mail)
            else:
                break
       
    def answer_userdefreq(self, req):
        answer = req.spec.upper()
        return answer 

    def get_role(self, peer):
        return self._roles[peer]


    def own_data_as_np_array(self):
        return self._data

    def own_labels_as_np_array(self):
        return self._labels
         


    def send_to_function_party(self, msg):
        self.send_to_peer(msg, self.FP_ID) 

    def send_to_peer(self, msg, peer):
        addr = self._addrs[peer]
        emsg = self._encode(msg)
        logging.debug("[instPeer] %s ready to send message of len %s to %s", self.own_peer_id, len(emsg), peer)
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.connect(addr)
            sock.sendall(emsg)

    def teardown(self):
        addr = self._addrs[self.own_peer_id]
        msghdr = struct.pack("!I", 1)
        emsg = msghdr + pickle.dumps(self.own_peer_id)
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.connect(addr)
            sock.sendall(emsg)
     
