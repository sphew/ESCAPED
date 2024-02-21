import numpy as np
from dataclasses import dataclass
from datetime import datetime
import logging
from typing import Literal
from .pfmsgs import *

@dataclass
class SelfMsg(PFMsg):
    msg_type: Literal['StartConv', 'TimeoutCheck', 'EndOnlinePhase'] = None
    peer: str = None


class ESCAPEDFunctionParty():

    TIMEOUT_THRESHOLD: int 
    FP_ID = 'function_party'
    peers = []


    def cooperate(self, labels=False): 
        self.dot_product_parts = {}
        self.label_parts = {}

        self.req_schedule = self._plan_requests(labels=labels) 
        logging.debug("[FP] will send the following requests: %s", self.req_schedule)
        self._nb_requests = len(self.req_schedule)
        self.teardown_req = PFRequestMsg(self._nb_requests+1, ReqType.Teardown) 

        self._pstates = {p : {'cur_req_id': 0, 'last_request': datetime.now(), 'still_active':True} for p in self.peers}
        for peer in self.peers:
            self.add_to_msg_queue(SelfMsg(0, 'StartConv', peer))
        self.add_to_msg_queue(SelfMsg(0, 'TimeoutCheck'))

        while not self.queue_empty():
            sender, msg = self.get_next_msg()
            self.handle_msg(msg, sender)
        
        logging.info("The function party successfully gathered all data from the input peers.")
    

    def send_next_request(self, req_id, peer):
        if req_id == self._nb_requests:
           self._pstates[peer]['still_active'] = False
           logging.info("[FP] Conversation with %s finished.", peer)
        else :
           req = self.req_schedule[req_id+1]
           self.send_to_peer(req, peer)
           self._pstates[peer]['cur_req_id'] = req_id+1
           self._pstates[peer]['last_request'] =  datetime.now()


    def handle_msg(self, msg, sender):
       
        req_id = msg.request_id
       
        # Message from self
        if msg.msg_type == 'StartConv':
            peer = msg.peer
            logging.info("[FP] Starting Conversation with %s.", peer)
            self.send_next_request(req_id, peer)
        
        elif msg.msg_type == 'EndOnlinePhase': 
            logging.info("[FP] Ending online phase.") 
            for peer in self.peers:
                self.send_to_peer(self.teardown_req, peer)

        elif msg.msg_type == 'TimeoutCheck':
            cur_time = datetime.now()
            ongoing_conversations = False 
            for peer, pstate in self._pstates.items():
                if pstate['still_active']:
                    ongoing_conversations = True
                    if (cur_time - pstate['last_request']).total_seconds() > self.TIMEOUT_THRESHOLD: 
                        req = self.req_schedule[pstate['cur_req_id']]
                        self.send_to_peer(req, peer)
                        pstate['last_request'] = datetime.now()
                        logging.info("[FP] Timeout. Resend request %i to %s.", req.request_id, peer)
            if ongoing_conversations:
                self.add_to_msg_queue(msg)
            else:
                self.add_to_msg_queue(SelfMsg(0, 'EndOnlinePhase'))

        else: # data from input party 
            peer = sender
            if self._pstates[peer]['cur_req_id'] > req_id:
                logging.debug("[FP] Got data of request %i from %s again. Ignore.", req_id, peer)
                return 

            elif msg.msg_type == MsgType.OwnGram:
                dot_product = msg.data
                logging.debug("[FP] Got dot_product from %s.", peer)
                pairing_id = (peer, peer)
                self.dot_product_parts[pairing_id] = (dot_product, np.zeros_like(dot_product))
    
            elif msg.msg_type == MsgType.AliceGram:
                pairing_id = msg.data.pairing_id
                component = msg.data.component
                unmasker = msg.data.unmasker
                logging.debug("[FP] Got dot product part ALICE from %s for %s", sender, pairing_id)
                if pairing_id in self.dot_product_parts:
                    c, u = self.dot_product_parts[pairing_id]
                    self.dot_product_parts[pairing_id] = (c + component, u * unmasker)
                else:
                    self.dot_product_parts[pairing_id] = (component, unmasker)
    
    
            elif msg.msg_type == MsgType.BobGram:
                pairing_id = msg.data.pairing_id
                component = msg.data.component
                unmasker = msg.data.unmasker
                logging.debug("[FP] Got dot product part BOB from %s for %s", sender, pairing_id)
                if pairing_id in self.dot_product_parts:
                    c, u = self.dot_product_parts[pairing_id]
                    self.dot_product_parts[pairing_id] = (c + component, u * unmasker)
                else:
                    self.dot_product_parts[pairing_id] = (component, unmasker)
    
            elif msg.msg_type == MsgType.Label: 
                labels = msg.data
                logging.debug("[FP] Got labels from %s", peer)
                self.label_parts[peer] = labels
            elif msg.msg_type == MsgType.UserDef: 
                self.handle_userdefmsg(msg, sender)
            else: 
                logging.warning("[FP]: Got message with unknown type %s.", msg.msg_type)
                return
            
            self.send_next_request(req_id, peer)

    def _plan_requests(self, labels):
        tasks = [(ReqType.YourGram,)] \
                 + [(ReqType.NextPeerGram,)] * (len(self.peers) - 1) \
                 + ( [(ReqType.Label,)] if labels else []) \
                 + [(ReqType.UserDef, req) for req in self.user_def_requests()]
        return {i+1: PFRequestMsg(i+1, *task) for i, task in enumerate(tasks)} 

    def get_dot_product(self, peers=None):
        if not peers:
            peers = self.peers
        arrlist = []
        for p1 in peers:
            row = []
            for p2 in peers:
                if (p1, p2) in self.dot_product_parts:
                    g1, g2 = self.dot_product_parts[(p1, p2)]
                    g = g1 + g2
                else:
                    g1, g2 = self.dot_product_parts[(p2, p1)]
                    g = np.transpose(g1 + g2)
                row.append(g)
            arr = np.concatenate(row, axis=1)
            arrlist.append(arr)
        dot_product = np.concatenate(arrlist, axis=0)
        return dot_product


    def handle_userdefmsg(self, msg, sender):
        pass



    def user_def_requests(self):
        return []

    def get_next_msg(self):
        pass

    def add_to_msg_queue(self, msg):
        pass

    def queue_empty(self):
        pass

    def send_to_peer(self, req, peer):
        pass



