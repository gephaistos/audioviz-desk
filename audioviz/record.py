import ctypes
import threading
import warnings

import numpy as np

from .pypulse import pa_simple_new, pa_simple_read, pa_simple_free, pa_usec_to_bytes, pa_simple_get_latency

from .pypulse import PaSampleSpec, PaSampleFormat, PaBufferAttr, PaSampleFormat, PaSampleSpec, PaChannelMap, PaBufferAttr, PaStreamDirection
from .filter import calc_freq_weights, calc_octave_freq_bounds, map_to_fft_freq_bounds, filter_signal, calc_uniform_freq_bounds


def open_connection(name: str, stream_name: str, ss: PaSampleSpec,
                    server: str|None = None, dev: str|None = None,
                    map: PaChannelMap|None = None, attr: PaBufferAttr|None = None) -> int:
    server = server.encode() if server is not None else server
    name = name.encode()
    dev = dev.encode() if dev is not None else dev
    stream_name = stream_name.encode()

    return pa_simple_new(server, name, PaStreamDirection.PA_STREAM_RECORD,
                         dev, stream_name, ss, map, attr)


def close_connection(s: int):
    pa_simple_free(s)


def make_buffer(sample_format: PaSampleFormat, num_samples: int):
    # TRY: maybe use bytearray and read all the data as chars
    # into it, then use np.frombuffer with appropriate dtype
    match sample_format:
        case PaSampleFormat.PA_SAMPLE_U8:
            buffer = (ctypes.c_uint8 * num_samples)()
        case PaSampleFormat.PA_SAMPLE_S16LE:
            buffer = (ctypes.c_int16 * num_samples)()
        case PaSampleFormat.PA_SAMPLE_FLOAT32LE:
            buffer = (ctypes.c_float * num_samples)()
        case PaSampleFormat.PA_SAMPLE_INVALID:
            raise ValueError('Invalid sample format!')
        case _:
            raise NotImplementedError(
                'Sorry, this sample format is not supported: {}'.format(sample_format)
            )

    return buffer


def fill_buffer(s: int, buffer: ctypes.Array):
    pa_simple_read(s, buffer, ctypes.sizeof(buffer))


def estimate_fragsize(dev: str|None, spec: PaSampleSpec, observations: int = 50) -> int:
    dev = dev.encode() if dev is not None else dev
    s = pa_simple_new(None, 'latency-tester'.encode(), PaStreamDirection.PA_STREAM_RECORD,
                      dev, 'latency-stream'.encode(), spec, None, None)
    stats = []
    for _ in range(observations):
        stats.append(pa_simple_get_latency(s))

    print('Estimated latency:', max(stats))

    pa_simple_free(s)

    fragsize = pa_usec_to_bytes(max(stats), spec)

    # Somewhy if connection latency is low (and thus is fragsize), some noises
    # are present in signal. Adding threshold seems to fix the issue.
    # If you still experience that, increase threshold,
    # but remember that the higher the fragsize, the worse the performance.
    if fragsize < 1000:
        fragsize = 1000
    if fragsize > 5000:
        fragsize = 5000
        warnings.warn('Warning! High connection latency, performance might be low.')

    return fragsize


class Recorder(threading.Thread):
    def __init__(self):
        super().__init__()
        self.connection = None

        self._stop_event = threading.Event()
        self._callbacks = []
        self._lock = threading.Lock()

        # configuring pulse recorder
        self.sample_format = PaSampleFormat.PA_SAMPLE_FLOAT32LE
        self.sample_frequency = 44100
        self.channels = 1

        self.pulse_config = {
            'name' : 'audioviz-app',
            'stream_name' : 'audio-recorder',
            'ss' : PaSampleSpec(self.sample_format.value, self.sample_frequency, self.channels),
            'server' : None,
            'dev' : None, # pass name if provided
            'map' : None,
            'attr' : None,
        }

        fragsize = estimate_fragsize(self.pulse_config['dev'], self.pulse_config['ss'])
        self.pulse_config['attr'] = PaBufferAttr(maxlength=-1, tlength=-1,
                                                 prebuf=-1, minreq=-1,
                                                 fragsize=fragsize)

        # configuring signal processing
        self.frame_size = 8192
        self.buffer_size = 512
        self.window_type = 'hanning'
        self.weighting_type = 'Z'
        self.num_bands = 'auto'

        # precalculations
        self.overlap = self.frame_size - self.buffer_size
        if self.window_type == 'hanning':
            self.window_type = np.hanning(self.frame_size)
        else:
            self.window_type = np.ones(self.frame_size)
        self.squared_window_sum = np.power(np.sum(self.window_type), 2.0)
        self.fft_freqs = np.fft.rfftfreq(self.frame_size, 1.0 / self.sample_frequency)
        self.fft_freq_weights = calc_freq_weights(self.fft_freqs, self.weighting_type)

        self.fft_size = self.fft_freqs.size

        if self.num_bands == 'auto':
            oct_freq_lower_bounds, oct_freq_upper_bounds = calc_octave_freq_bounds(fraction=3)
            self.band_freq_weights = calc_freq_weights(
                (oct_freq_lower_bounds + oct_freq_upper_bounds) / 2.0, self.weighting_type
            )
            self.fft_freq_lower_bounds, self.fft_freq_upper_bounds = map_to_fft_freq_bounds(
                oct_freq_lower_bounds, oct_freq_upper_bounds, self.fft_size
            )
        else:
            self.fft_freq_lower_bounds, self.fft_freq_upper_bounds = calc_uniform_freq_bounds(
                self.fft_size, self.num_bands
            )
            self.band_freq_weights = calc_freq_weights(
                (self.fft_freq_lower_bounds + self.fft_freq_upper_bounds) / 2.0,
                self.weighting_type
            )

        # create buffers
        self.buffer = make_buffer(self.sample_format, self.buffer_size)
        self.frame = np.zeros(self.frame_size, dtype='f')
        self.fft_mags = np.zeros(self.fft_size, dtype=np.float32)
        self.band_mags = np.ones(self.band_freq_weights.size)


    def run(self):
        try:
            self.connect()
            while not self._stop_event.is_set():
                with self._lock:
                    fill_buffer(self.connection, self.buffer)
                    filter_signal(self.frame, self.buffer, self.overlap, self.buffer_size,
                                    self.fft_mags, self.window_type,
                                    self.squared_window_sum,
                                    self.fft_freq_weights,
                                    self.band_mags, self.band_freq_weights,
                                    self.fft_freq_lower_bounds, self.fft_freq_upper_bounds)
                    for callback in self._callbacks:
                        callback()
        except Exception as e:
            self.disconnect()
            raise e
        else:
            self.disconnect()

    def stop(self):
        self._stop_event.set()

    def add_callback(self, callback):
        self._callbacks.append(callback)

    def connect(self):
        self.connection = open_connection(**self.pulse_config)
        print('Connection established')

        # jit cache warm-up
        fill_buffer(self.connection, self.buffer)
        filter_signal(self.frame, self.buffer, self.overlap, self.buffer_size,
                      self.fft_mags, self.window_type,
                      self.squared_window_sum,
                      self.fft_freq_weights,
                      self.band_mags, self.band_freq_weights,
                      self.fft_freq_lower_bounds, self.fft_freq_upper_bounds)


    def disconnect(self):
        close_connection(self.connection)
        print('Connection closed')
