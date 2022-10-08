import abc
import json
import logging
import os
import re
import socket
from collections import namedtuple
from threading import Thread
from types import coroutine
from typing import List

from taro import paths

RECV_BUFFER_LENGTH = 16384
prefixed_payload_regex = re.compile(b'^(\\d+)(.*)')

log = logging.getLogger(__name__)


class SocketServer(abc.ABC):

    def __init__(self, socket_name):
        self._socket_name = socket_name
        self._server: socket = None
        self._stopped = False

    def start(self) -> bool:
        if self._stopped:
            return False
        try:
            socket_path = paths.socket_path(self._socket_name, create=True)
        except FileNotFoundError as e:
            log.error("event=[unable_create_socket_dir] socket_dir=[%s] message=[%s]", e.filename, e)
            return False

        self._server = socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM)
        try:
            self._server.bind(str(socket_path))
            Thread(target=self.serve, name='Thread-ApiServer').start()
            return True
        except PermissionError as e:
            log.error("event=[unable_create_socket] socket=[%s] message=[%s]", socket_path, e)
            return False

    def serve(self):
        log.debug('event=[server_started]')
        while not self._stopped:
            payload, client_address = self._receive_full_datagram()
            if not payload:
                break

            req_body = json.loads(payload)
            resp_body = self.handle(req_body)

            if resp_body:
                if client_address:
                    self._server.sendto(json.dumps(resp_body).encode(), client_address)
                else:
                    log.warning('event=[missing_client_address]')

        log.debug('event=[server_stopped]')

    def _receive_full_datagram(self):
        payload_length = 0
        payload = b''
        client_address = None
        while not payload or len(payload) < payload_length:
            datagram, client_address = self._server.recvfrom(RECV_BUFFER_LENGTH)  # Client address guaranteed be same?

            if not datagram:
                return None, None

            match = prefixed_payload_regex.match(datagram)
            if match:
                if payload:  # Unsure if this can ever happen
                    log.warning(f"event=[incomplete_datagram] client=[{client_address}]")
                payload_length = match.group(1)
                payload = match.group(2)
            else:
                payload += datagram

        return payload, client_address

    @abc.abstractmethod
    def handle(self, req_body):
        """
        Handle request and optionally return response
        :return: response body or None if no response
        """

    def stop(self):
        self._stopped = True

    def close(self):
        self.stop()

        if self._server is None:
            return

        socket_name = self._server.getsockname()
        try:
            self._server.shutdown(socket.SHUT_RD)
            self._server.close()
        finally:
            if os.path.exists(socket_name):
                os.remove(socket_name)


InstanceResponse = namedtuple('InstanceResponse', 'instance response')


class SocketClient:

    def __init__(self, file_extension: str, bidirectional: bool):
        self._file_extension = file_extension
        self._bidirectional = bidirectional
        self._client = socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM)
        if bidirectional:
            self._client.bind(self._client.getsockname())
        self.dead_sockets = []

    @coroutine
    def servers(self, include=()):
        req_body = '_'  # Dummy initialization to remove warnings
        resp = None
        skip = False
        for api_file in paths.socket_files(self._file_extension):
            instance_id = api_file.stem
            if (api_file in self.dead_sockets) or (include and instance_id not in include):
                continue
            while True:
                if not skip:
                    req_body = yield resp
                skip = False  # reset
                if not req_body:
                    break  # next(this) called -> proceed to the next server
                try:
                    self._client.sendto(json.dumps(req_body).encode(), str(api_file))
                    if self._bidirectional:
                        datagram = self._client.recv(RECV_BUFFER_LENGTH)
                        resp = InstanceResponse(instance_id, json.loads(datagram.decode()))
                except ConnectionRefusedError:  # TODO what about other errors?
                    log.warning('event=[dead_socket] socket=[{}]'.format(api_file))
                    self.dead_sockets.append(api_file)
                    skip = True  # Ignore this one and continue with another one
                    break

    def communicate(self, req, include=()) -> List[InstanceResponse]:
        server = self.servers(include=include)
        responses = []
        while True:
            try:
                next(server)
                responses.append(server.send(req))  # StopIteration is raised from this function if last socket is dead
            except StopIteration:
                break
        return responses

    def close(self):
        self._client.shutdown(socket.SHUT_RDWR)
        self._client.close()
