import numpy as np 
import logging
from collections import deque
import socket
import selectors
import struct
import pickle


class Message():

    HDRLEN = 4
    EMPTY_MSG = bytearray(4)
    CHUNKSIZE = 4096

    def __init__(self, selector, sock, addr, outbuf):
        self.selector = selector
        self.sock = sock
        self.addr = addr
        self.outbuf = outbuf
        self._recv_chunks = []
        self._recv_chunks_size = 0
        self._recv_buffer = b""
        self._send_buffer = b""
        self._content_len = None
        self.content = None
        self.response_created = False

    def _set_selector_events_mask(self, mode):
        if mode == "r":
            events = selectors.EVENT_READ
        elif mode == "w":
            events = selectors.EVENT_WRITE
        elif mode == "rw":
            events = selectors.EVENT_READ | selectors.EVENT_WRITE
        else:
            raise ValueError(f"[Msg]: Invalid events mask mode {mode!r}")
        self.selector.modify(self.sock, events, data=self)


    def process_events(self, mask):
        if mask & selectors.EVENT_READ:
            return self.read()
        if mask & selectors.EVENT_WRITE:
            self.write()

    def read(self):
        self._read()
        
        if self._content_len is None:
            self.process_lenheader()
       
        if self._content_len is not None:
            if self._content_len == 1: # client teardown
                client_id = pickle.loads(self._recv_buffer)
                return client_id
            elif self._content_len: # client sends msg to mailbox 
                if self.content is None:
                    self.process_content()
            else: # client checks its mailbox 
                self._set_selector_events_mask("w")


    def _read(self):
        try:
            chunk = self.sock.recv(self.CHUNKSIZE)
        except BlockingIOError:
            pass
        else:
            if chunk:
                self._recv_chunks.append(chunk)
                self._recv_chunks_size += len(chunk)
            else: 
                raise RuntimeError("Peer closed connection")

    def process_lenheader(self):
        self._recv_buffer += b''.join(self._recv_chunks)
        self._recv_chunks.clear()
        self._recv_chunks_size = 0
        if len(self._recv_buffer) >= self.HDRLEN:
            self._content_len = struct.unpack("!I", self._recv_buffer[:self.HDRLEN])[0]
            self._recv_buffer = self._recv_buffer[self.HDRLEN:]

    def process_content(self):
        conlen = self._content_len
        if len(self._recv_buffer) + self._recv_chunks_size >= conlen:
            self._recv_buffer += b''.join(self._recv_chunks)
            self._recv_chunks.clear()
            self._recv_chunks_size = 0
            self.content = self._recv_buffer[:conlen]
            self._recv_buffer = self._recv_buffer[conlen:]
            self.outbuf.append(self.content)
            self.close()


    def write(self):
        if not self.response_created:
            self.create_response()
        self._write()

    def _write(self):
        if self._send_buffer:
            try:
                sent = self.sock.send(self._send_buffer)
            except BlockingIOError:
                pass
            else:
                self._send_buffer = self._send_buffer[sent:]
                if sent and not self._send_buffer:
                    self.close()

    def create_response(self):
        if self.outbuf:
            msg = self.outbuf.pop()
            msg = struct.pack("!I", len(msg)) + msg
        else:
            msg = self.EMPTY_MSG 
        self._send_buffer += msg
        self.response_created = True


    def close(self):
        try:
            self.selector.unregister(self.sock)
        except Exception as e:
            print(f"[Msg] Error: selector.unregister() exception for {self.addr}: {e!r}")
        try:
            self.sock.close()
        except OSError as e:
            print(f"[Msg] Error: socket.close() exception for {self.addr}: {e!r}")
        finally:
            self.sock = None





class Connserver():

    FP_ID = 'function_party'

    def __init__(self, connaddr, client_ids):

        self.host, self.port = connaddr 
        self.sel  = selectors.DefaultSelector()

        self.client_ids = client_ids 
        nbclients = len(client_ids)

        # for each participant, create one listening socket
        self.socks = {cname: socket.socket(socket.AF_INET, socket.SOCK_STREAM) for cname in self.client_ids}
        self.socks[self.FP_ID] = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        for s in self.socks.values():
            s.bind((self.host, 0))
            s.listen()
            s.setblocking(False) 
            self.sel.register(s, selectors.EVENT_READ, data=None)

        # create address table
        self.address_table = {sname : s.getsockname() for sname, s in self.socks.items()}
        logging.debug("[Connserver] Client addresses: %s", self.address_table)

        # each participant starts with an empty mailbox
        self.msgbuffers = {addr[1]: [] for addr in self.address_table.values()}

        # The primary listening socket of the connector will spread the address table to the participants
        self.lsock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.lsock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.lsock.bind((self.host, self.port))
        self.lsock.listen()
        self.lsock.setblocking(False)
        self.sel.register(self.lsock, selectors.EVENT_READ, data=None)
        
        # put initialization msgs in queue of listening socket
        self.msgbuffers[self.port] = [pickle.dumps(m) for m in self._create_init_msgs(nbclients)] 

    def _create_init_msgs(self, nb_clients):
        msgs = [self.address_table]*(nb_clients+1)
        return msgs

    def run(self):
        clients_running = {c : True for c in self.client_ids}
        c = 0
        try:
            while any(clients_running.values()):
                events = self.sel.select(timeout=None)
                for key, mask in events:
                    if key.data is None:
                        self.accept_wrapper(key.fileobj)
                    else:
                        message = key.data
                        try:
                            client_dropout = message.process_events(mask)
                            if client_dropout:
                                clients_running[client_dropout] = False
                                message.close()
                        except Exception as e:
                            logging.error("[Connserver]: Exception for %s : %s", message.addr, e)
                            message.close()
            self.sel.unregister(self.lsock)
            self.sel.close()
        except KeyboardInterrupt:
            logging.error("[Connserver]: Keyboard interrupt")
        finally:
            self.sel.close()

    def accept_wrapper(self, sock):
        conn, addr = sock.accept()
        sockport = sock.getsockname()[1]
        conn.setblocking(False)
        message = Message(self.sel, conn, addr, self.msgbuffers[sockport]) 
        self.sel.register(conn, selectors.EVENT_READ, data=message)


