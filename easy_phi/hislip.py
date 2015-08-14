#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Implementation of HiSLIP protocol based on tornado.TCPServer

Protocol specification can be found here:
http://www.ivifoundation.org/downloads/Class%20Specifications/IVI-6.1_HiSLIP-1.1-2011-02-24.pdf
"""

import struct

import tornado.tcpserver
from tornado.options import options, define

# from easy_phi import hwal

# timeout on network communications in seconds
# since all messages are less than 500b, 1 second should be more than enough
# bigger timeout allows to DDOS system by slow connections
define('hislip_timeout', 1)
define('hislip_max_message_size', 4096)


class HiSLIPMessageCodes(object):
    """Class to store constant values of HiSLIP messages type (3rd byte) """
    Initialize = 0  # sync/client
    InitializeResponse = 1  # sync/server
    FatalError = 2  # sync (contradicting spec, may be either/either)
    Error = 3  # sync (contradicting spec, may be either/either)
    AsyncLock = 4  # async/client
    AsyncLockResponse = 5  # async/server
    Data = 6  # sync/either
    DataEnd = 7  # sync/either
    DeviceClearComplete = 8  # sync/client
    DeviceClearAcknowledge = 9  # sync/server
    AsyncRemoteLocalControl = 10  # async/client
    AsyncRemoteLocalResponse = 11  # async/server
    Trigger = 12  # sync/client
    Interrupted = 13  # sync/server
    AsyncInterrupted = 14  # async/server
    AsyncMaximumMessageSize = 15  # async/client
    AsyncMaximumMessageSizeResponse = 16  # async/server
    AsyncInitialize = 17  # async/client
    AsyncInitializeResponse = 18  # async/server
    AsyncDeviceClear = 19  # async/client
    AsyncServiceRequest = 20  # async/server
    AsyncStatusQuery = 21  # async/client
    AsyncStatusResponse = 22  # async/server
    AsyncDeviceClearAcknowledge = 23  # async/server
    AsyncLockInfo = 24  # async/client
    AsynchLockInfoResponse = 25  # async/server
    # 26..127 reserved for future use
    # 128..255 are vendor specific


class HiSLIPErrorCodes(object):
    """Class to store constant values of HiSLIP error codes """
    UndefinedError = 0
    PoorlyFormedMessageHeader = 1
    AttemptToUseConnWithoutBothChannelsEstablished = 0
    InvalidInitializationSequence = 0
    MaxClientsExceeded = 0
    # 5..127 reserved for HiSLIP extensions
    # 128..255 Device-defined errors


class HiSLIPBadMessage(IOError):
    """Exception to indicate malformed message"""


class HiSLIPCommError(IOError):
    """Exception to indicate communication issues, such as timeout"""


class HiSLIPSession(object):
    id = None


class HiSLIPMessage(object):

    type = 0  # 1 byte, subset of HiSLIPMessageCodes properties
    control_code = 0
    parameter = 0
    payload = ''

    def __init__(self, mtype, control_code=0, parameter=0, payload=''):
        self.type = mtype
        self.control_code = control_code
        self.parameter = parameter
        self.payload = payload

    @property
    def parameter_lword(self):
        return self.parameter & 0xffff

    @parameter_lword.setter
    def parameter_lword(self, word):
        self.parameter = ((self.parameter & 0xffff) ^ self.parameter) | \
                         (word & 0xffff)

    @property
    def parameter_uword(self):
        return self.parameter >> 16

    @parameter_uword.setter
    def parameter_uword(self, word):
        self.parameter = ((self.parameter & 0xffff0000) ^ self.parameter) | \
                         ((word & 0xffff) << 16)

    @staticmethod
    def from_stream(stream):
        """
        :param connection: tornado.iostream.IOStream
        """
        header = stream.read_bytes(16)

        # these exceptions should be handled by caller to return corresponding
        # error message or close connection
        if len(header) < 16:
            raise HiSLIPCommError('HiSLIP communication timeout')
        if header[0:2] != b'HS':
            raise HiSLIPBadMessage('Poorly formed message header')

        mtype, control_code, parameter, payload_length = \
            struct.unpack('bbIQ', header)

        if payload_length > options.hislip_max_message_size:
            raise HiSLIPBadMessage('HiSLIP message exceeds max allowed size')

        payload = stream.read_bytes(payload_length)

        if len(payload) < payload_length:
            raise HiSLIPCommError('HiSLIP communication timeout')

        return HiSLIPMessage(mtype, control_code, parameter, payload)

    def __str__(self):
        return struct.pack('bbIQ', self.type, self.control_code,
                           self.parameter, len(self.payload)) + self.payload

# context:
# protocol version
# message id
# session id if async not established yet



class HiSLIPServer(tornado.tcpserver.TCPServer):

    sessions = []

    def handle_stream(self, stream, address):
        """

        :param stream: tornado.iostream.IOStream instance. We need to write
                response to stream.socket
        :param address: remote address. It is not important for us
        :return: None
        """

        try:
            # stream.socket is connection after conn, addr = socket.accept()
            # Stacktrace:
            # L143@tornado.tcpserver.TCPServer.add_sockets()
            # L253@tornado.netutil.add_handler()
            # L266@tornado.tcpserver.TCPServer._handle_connection()
            # L986@tornado.iostream.IOStream.__init__()
            message = HiSLIPMessage.from_stream(stream)
        except HiSLIPBadMessage:  # not a HiSLIP message
            stream.close()
            # TODO: respond with error message
            return
        except HiSLIPCommError:
            stream.close()
            # TODO: log exception
            return

        if message.type == HiSLIPMessageCodes.Initialize:
            pass
