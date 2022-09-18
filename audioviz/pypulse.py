"""Wrapper for pulse-simple library
https://freedesktop.org/software/pulseaudio/doxygen/simple_8h.html
"""


import ctypes.util
from ctypes import (
    POINTER, Structure, c_char_p, c_int, c_size_t, c_uint8, c_uint32, c_uint64, c_void_p
)
from enum import Enum, unique


_libpulse_simple = None


class PaSampleSpec(Structure):
    """Wraps `pa_sample_spec` structure.
    """
    _fields_ = [
        ('format', c_uint32),  # gets PaSampleFormat
        ('rate', c_uint32),
        ('channels', c_uint8)
    ]


class PaChannelMap(Structure):
    _fields_ = [
        ('channels', c_uint8),
        ('map', c_uint32)  # gets PaChannelPosition
    ]


class PaBufferAttr(Structure):
    _fields_ = [
        ('maxlength', c_uint32),
        ('tlength', c_uint32),
        ('prebuf', c_uint32),
        ('minreq', c_uint32),
        ('fragsize', c_uint32)
    ]


# https://www.freedesktop.org/wiki/Software/PulseAudio/Documentation/User/SupportedAudioFormats/
@unique
class PaSampleFormat(Enum):
    PA_SAMPLE_U8 = 0
    PA_SAMPLE_ALAW = 1
    PA_SAMPLE_ULAW = 2
    PA_SAMPLE_S16LE = 3
    PA_SAMPLE_S16BE = 4
    PA_SAMPLE_FLOAT32LE = 5
    PA_SAMPLE_FLOAT32BE = 6
    PA_SAMPLE_S32LE = 7
    PA_SAMPLE_S32BE = 8
    PA_SAMPLE_S24LE = 9
    PA_SAMPLE_S24BE = 10
    PA_SAMPLE_S24_32LE = 11
    PA_SAMPLE_S24_32BE = 12
    PA_SAMPLE_MAX = 13
    PA_SAMPLE_INVALID = 14


@unique
class PaChannelPosition(Enum):
    PA_CHANNEL_POSITION_INVALID = -1
    PA_CHANNEL_POSITION_MONO = 0
    PA_CHANNEL_POSITION_FRONT_LEFT = 1
    PA_CHANNEL_POSITION_FRONT_RIGHT = 2
    PA_CHANNEL_POSITION_FRONT_CENTER = 3
    PA_CHANNEL_POSITION_REAR_CENTER = 4
    PA_CHANNEL_POSITION_REAR_LEFT = 5
    PA_CHANNEL_POSITION_REAR_RIGHT = 6
    PA_CHANNEL_POSITION_LFE = 7
    PA_CHANNEL_POSITION_FRONT_LEFT_OF_CENTER = 8
    PA_CHANNEL_POSITION_FRONT_RIGHT_OF_CENTER = 9
    PA_CHANNEL_POSITION_SIDE_LEFT = 10
    PA_CHANNEL_POSITION_SIDE_RIGHT = 11
    PA_CHANNEL_POSITION_AUX0 = 12
    PA_CHANNEL_POSITION_AUX1 = 13
    PA_CHANNEL_POSITION_AUX2 = 14
    PA_CHANNEL_POSITION_AUX3 = 15
    PA_CHANNEL_POSITION_AUX4 = 16
    PA_CHANNEL_POSITION_AUX5 = 17
    PA_CHANNEL_POSITION_AUX6 = 18
    PA_CHANNEL_POSITION_AUX7 = 19
    PA_CHANNEL_POSITION_AUX8 = 20
    PA_CHANNEL_POSITION_AUX9 = 21
    PA_CHANNEL_POSITION_AUX10 = 22
    PA_CHANNEL_POSITION_AUX11 = 23
    PA_CHANNEL_POSITION_AUX12 = 24
    PA_CHANNEL_POSITION_AUX13 = 25
    PA_CHANNEL_POSITION_AUX14 = 26
    PA_CHANNEL_POSITION_AUX15 = 27
    PA_CHANNEL_POSITION_AUX16 = 28
    PA_CHANNEL_POSITION_AUX17 = 29
    PA_CHANNEL_POSITION_AUX18 = 30
    PA_CHANNEL_POSITION_AUX19 = 31
    PA_CHANNEL_POSITION_AUX20 = 32
    PA_CHANNEL_POSITION_AUX21 = 33
    PA_CHANNEL_POSITION_AUX22 = 34
    PA_CHANNEL_POSITION_AUX23 = 35
    PA_CHANNEL_POSITION_AUX24 = 36
    PA_CHANNEL_POSITION_AUX25 = 37
    PA_CHANNEL_POSITION_AUX26 = 38
    PA_CHANNEL_POSITION_AUX27 = 39
    PA_CHANNEL_POSITION_AUX28 = 40
    PA_CHANNEL_POSITION_AUX29 = 41
    PA_CHANNEL_POSITION_AUX30 = 42
    PA_CHANNEL_POSITION_AUX31 = 43
    PA_CHANNEL_POSITION_TOP_CENTER = 44
    PA_CHANNEL_POSITION_TOP_FRONT_LEFT = 45
    PA_CHANNEL_POSITION_TOP_FRONT_RIGHT = 46
    PA_CHANNEL_POSITION_TOP_FRONT_CENTER = 47
    PA_CHANNEL_POSITION_TOP_REAR_LEFT = 48
    PA_CHANNEL_POSITION_TOP_REAR_RIGHT = 49
    PA_CHANNEL_POSITION_TOP_REAR_CENTER = 50
    PA_CHANNEL_POSITION_MAX = 51


@unique
class PaStreamDirection(Enum):
    PA_STREAM_NODIRECTION = 0
    PA_STREAM_PLAYBACK = 1
    PA_STREAM_RECORD = 2
    PA_STREAM_UPLOAD = 3


def load_libpulse_simple():
    global _libpulse_simple
    try:
        _libpulse_simple = ctypes.CDLL(ctypes.util.find_library('pulse-simple')
                                       or 'libpulse-simple.so.0')
    except OSError as err:
        raise ImportError('{}: {}'.format(type(err), err))


def wrap_libpulse_simple():
    load_libpulse_simple()

    # `pa_simple` struct is void*
    _libpulse_simple.pa_simple_new.argtypes = [
        c_char_p,  # server
        c_char_p,  # name
        c_uint32,  # dir, gets PaStreamDirection
        c_char_p,  # dev
        c_char_p,  # stream_name
        POINTER(PaSampleSpec),  # ss
        POINTER(PaChannelMap),  # map
        POINTER(PaBufferAttr),  # attr
        POINTER(c_int)  # error
    ]
    _libpulse_simple.pa_simple_new.restype = c_void_p  # s, `pa_simple`

    _libpulse_simple.pa_simple_free.argtypes = [
        c_void_p  # s
    ]

    _libpulse_simple.pa_simple_write.argtypes = [
        c_void_p,  # s
        c_void_p,  # data
        c_size_t,  # bytes
        POINTER(c_int)  # error
    ]

    _libpulse_simple.pa_simple_drain.argtypes = [
        c_void_p,  # s
        POINTER(c_int)  # error
    ]

    _libpulse_simple.pa_simple_read.argtypes = [
        c_void_p,  # s
        c_void_p,  # data
        c_size_t,  # bytes
        POINTER(c_int)  # error
    ]

    _libpulse_simple.pa_simple_get_latency.argtypes = [
        c_void_p,  # s
        POINTER(c_int)  # error
    ]
    _libpulse_simple.pa_simple_get_latency.restype = c_uint64  # `pa_usec_t`

    _libpulse_simple.pa_simple_flush.argtypes = [
        c_void_p,  # s
        POINTER(c_int)  # error
    ]


wrap_libpulse_simple()


def pa_simple_new(server: str|None, name: str, dir: PaStreamDirection,
                  dev: str|None, stream_name: str, ss: PaSampleSpec,
                  map: PaChannelMap|None, attr: PaBufferAttr|None, error: int = 0) -> int:
    """Create a new connection to the server.

    Parameters
    ----------
    server : str | None
        Server name, or NULL for default
    name : str
        A descriptive name for this client (application name, ...)
    dir : PaStreamDirection
        Open this stream for recording or playback?
    dev : str | None
        Sink (resp. source) name, or NULL for default
    stream_name : str
        A descriptive name for this stream (application name, song title, ...)
    ss : PaSampleSpec
        The sample type to use
    map : PaChannelMap | None
        The channel map to use, or NULL for default
    attr : PaBufferAttr | None
        Buffering attributes, or NULL for default
    error : int, optional
        A pointer where the error code is stored
        when the routine returns NULL, by default 0

    Returns
    -------
    int
        The connection object

    Raises
    ------
    Exception
        If failed to create stream
    """
    server = server.encode() if server is not None else server
    name = name.encode()
    dir = dir.value
    dev = dev.encode() if dev is not None else dev
    stream_name = stream_name.encode()
    error = c_int(error)

    connection = _libpulse_simple.pa_simple_new(server, name, dir, dev,
                                                stream_name, ss, map, attr, error)
    if not connection:
        raise Exception('Failed to create stream: {}'.format(error.value))

    return connection


def pa_simple_free(s: int):
    """Close and free the connection to the server.

    Parameters
    ----------
    s : int
        The connection object
    """
    _libpulse_simple.pa_simple_free(s)


def pa_simple_write(s: int, data, bytes: int, error: int = 0):
    error = c_int(error)
    ret = _libpulse_simple.pa_simple_write(s, data, bytes, error)

    if ret < 0:
        raise Exception('Failed to write data to stream: {}'.format(error.value))


def pa_simple_drain(s: int, error: int = 0):
    error = c_int(error)
    ret = _libpulse_simple.pa_simple_drain(s, error)

    if ret < 0:
        raise Exception('Failed to drain stream data: {}'.format(error.value))


def pa_simple_read(s: int, data, bytes: int, error: int = 0):
    error = c_int(error)
    ret = _libpulse_simple.pa_simple_read(s, data, bytes, error)

    if ret < 0:
        raise Exception('Failed to read data from stream: {}'.format(error.value))


def pa_simple_get_latency(s: int, error: int = 0) -> int:
    error = c_int(error)
    latency = _libpulse_simple.pa_simple_get_latency(s, error)

    if error != 0:
        raise Exception('Failed to get latency: {}'.format(error.value))

    return latency.value


def pa_simple_flush(s: int, error: int = 0):
    error = c_int(error)
    ret = _libpulse_simple.pa_simple_flush(s, error)

    if ret < 0:
        raise Exception('Failed to flush buffer: {}'.format(error.value))