import numpy as np
import logging
from datetime import datetime
from collections import deque
from enum import Enum
from .ppmsgs import *
from .pfmsgs import *


PPRole = Enum('PPRole', ['Alice', 'Bob'])

class ESCAPEDPeer():

    FP_ID = 'function_party'
    RAND_MIN: int 
    RAND_MAX: int 
    TIMEOUT_THRESHOLD: int 
    own_peer_id: str 
    peers = []

    def cooperate(self):

        # init own data and masked data
        self.__data = self.own_data_as_np_array()
        self.__own_dot_product = self.__data @ np.transpose(self.__data)
        self.__masker = np.random.uniform(self.RAND_MIN, self.RAND_MAX, self.__data.shape)
        self.__alpha = np.random.uniform(self.RAND_MIN,  self.RAND_MAX, (1))
        masked_data = self.__data - self.__masker
        partial_unmasker = self.__alpha * self.__masker
        self.alice_msg = AliceToBobMsg(PPMsgType.AliceMasked, masked_data, partial_unmasker)
        self.bob_msg = BobToAliceMsg(PPMsgType.BobMasked, masked_data)
        
        # init output buffer
        self._pgrams = deque() 
        self._cur_fp_msg = None
        self._cur_fp_req_id = 0
        # init state 
        self._still_waiting = {peer: True for peer in self.peers}
        self._last_timeout_check = datetime.now()
        self._teardown = False
       
        # send data to all peers
        for peer in self.peers:
            self.share_masked_data(peer)

        # handle requests 
        while not self._teardown:
            sender, msg = self.get_next_msg()
            if sender == self.FP_ID: 
                self.handle_fp_req(msg)
            elif sender in self.peers:
                self.handle_msg(sender, msg)
            elif sender:
                logging.warning("[Peer] %s. Got message from unknown or undecipherable sender %s.", self.own_peer_id, sender)
            else:
                pass # idle, waiting for messages
                
        self.teardown()

    def share_masked_data(self, peer):
            role = self.get_role(peer)
            if role == PPRole.Alice:
                 self.send_to_peer(self.alice_msg, peer)
            elif role == PPRole.Bob:
                 self.send_to_peer(self.bob_msg, peer)
            else:
                logging.error("[Peer] No valid role: %s", role)


    def handle_fp_req(self, req):
        self.timeout_check()
        req_id = req.request_id
        if self._cur_fp_req_id > req_id:
            logging.info("[Peer] %s got request %s again. Has already been answered. Will do nothing.", self.own_peer_id, req_id)
            return
        if self._cur_fp_req_id == req_id:
            logging.info("[Peer] %s got request %s again. Resend data to function party.", self.own_peer_id, req_id)
            self.send_to_function_party(self._cur_fp_msg)
            return
        if req.req_type == ReqType.YourGram:
            logging.debug("[Peer] %s got request for own gram", self.own_peer_id)
            msg = PFDataMsg(req_id, MsgType.OwnGram, self.__own_dot_product)
            self._cur_fp_msg = msg
            self._cur_fp_req_id = req_id
            self.send_to_function_party(self._cur_fp_msg)
        elif req.req_type == ReqType.NextPeerGram:
            logging.debug("[Peer] %s get request for next gram part", self.own_peer_id)
            try:
                mtype, peergram = self._pgrams.popleft()
                msg = PFDataMsg(req_id, mtype, peergram)
                self._cur_fp_msg = msg
                self._cur_fp_req_id = req_id
                self.send_to_function_party(self._cur_fp_msg)
            except:
                logging.info("[Peer] %s got request for next gram part, but no part is ready yet.", self.own_peer_id)
        elif req.req_type == ReqType.Label:
            mtype = MsgType.Label
            data = self.own_labels_as_np_array()
            msg = PFDataMsg(req_id, mtype, data)
            self._cur_fp_msg = msg
            self._cur_fp_req_id = req_id
            self.send_to_function_party(self._cur_fp_msg)
        elif req.req_type == ReqType.UserDef:
            mtype= MsgType.UserDef
            data  = self.answer_userdefreq(req)
            msg = PFDataMsg(req_id, mtype, data)
            self._cur_fp_msg = msg
            self._cur_fp_req_id = req_id
            self.send_to_function_party(self._cur_fp_msg)
        elif req.req_type == ReqType.Teardown:
            logging.info("[Peer] %s got teardown request.", self.own_peer_id)
            self._teardown = True
        else:
            logging.warning("[Peer] %s got unexpected request of type %s. Will do nothing.", self.own_peer_id, req.req_type)

    def answer_userdefreq(self, req):
        pass

    

    def handle_msg(self, sender, msg):
        peer = sender
        if self._still_waiting[peer]:
            if msg.msg_type == PPMsgType.AliceMasked:
                logging.debug("[Peer] %s got data from ALICE %s", self.own_peer_id, peer)
                pairing_id = (peer, self.own_peer_id)
                component = msg.masked_data @ np.transpose(self.__data)
                unmasker = msg.partial_unmasker @ np.transpose(self.__masker)
                peergram = PeerGram(pairing_id, component, unmasker)
                mtype = MsgType.BobGram
                self._pgrams.append((mtype, peergram))
                self._still_waiting[peer] = False
            elif msg.msg_type == PPMsgType.BobMasked:
                logging.debug("[Peer] %s got data from BOB %s", self.own_peer_id, peer)
                pairing_id = (self.own_peer_id, peer)
                component = self.__masker @ np.transpose(msg.masked_data)
                unmasker = 1.0/self.__alpha
                peergram = PeerGram(pairing_id, component, unmasker)
                mtype = MsgType.AliceGram
                self._pgrams.append((mtype, peergram))
                self._still_waiting[peer] = False
            elif msg.msg_type == PPMsgType.Request:
                logging.info("[Peer] %s got resend request from %s. Will resend data.", self.own_peer_id, peer)
                self.share_masked_data(peer)
            else:
                logging.warning("[Peer] %s got unexpected message from %s of type %s. Will do nothing.", self.own_peer_id, peer, msg.msg_type)
        else:
            logging.info("[Peer] %s got data from %s again. Ignore", self.own_peer_id, peer)


    def timeout_check(self):
        cur_time = datetime.now()
        if (cur_time - self._last_timeout_check).total_seconds() > self.TIMEOUT_THRESHOLD:
            for peer, waiting in self._still_waiting.items():
                if waiting:
                    msg = PPMsg(PPMsgType.Request)
                    self.send_to_peer(msg, peer)
                    logging.info("[Peer] %s Timeout. Resend request to peer %s", self.own_peer_id, peer)
        self._last_timeout_check = cur_time

                



    def get_next_msg(self):
        pass

    def get_role(self, peer):
        pass

    def own_data_as_np_array(self):
        pass

    def own_labels_as_np_array(self):
        pass

    def send_to_function_party(self, msg):
        #sending functions have to add id!
        pass

    def send_to_peer(self, msg, peer):
        #sending functions have to add id!
        pass 

    def teardown(self):
        pass


