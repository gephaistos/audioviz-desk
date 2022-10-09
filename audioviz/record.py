import ctypes
import threading
import warnings

import numpy as np

from .pypulse import pa_simple_new, pa_simple_read, pa_simple_free, pa_usec_to_bytes, pa_simple_get_latency

from .pypulse import PaSampleSpec, PaSampleFormat, PaBufferAttr, PaSampleFormat, PaSampleSpec, PaChannelMap, PaBufferAttr, PaStreamDirection
from .filter import calc_octave_freq_bounds, map_to_fft_bounds
from .filter import filter_signal, calc_freq_amplifier, calc_logspace_fft_bounds

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
    def __init__(self, config: dict):
        super().__init__()
        self.connection = None

        # pulse recorder
        self.sample_format = PaSampleFormat.PA_SAMPLE_FLOAT32LE # try PA_SAMPLE_S16LE
        self.sample_frequency = config['frequency']
        self.channels = config['channels']

        self.pulse_config = {
            'name' : 'audioviz-app',
            'stream_name' : 'audio-recorder',
            'ss' : PaSampleSpec(self.sample_format.value, self.sample_frequency, self.channels),
            'server' : None,
            'dev' : None if config['device'] == 'None' else config['device'],
            'map' : None,
            'attr' : None,
        }

        fragsize = estimate_fragsize(self.pulse_config['dev'], self.pulse_config['ss'])
        # fragsize = 8 * buffer_size * channels * sample_format / 8 * 2
        self.pulse_config['attr'] = PaBufferAttr(maxlength=-1, tlength=-1,
                                                 prebuf=-1, minreq=-1,
                                                 fragsize=fragsize)

        # signal processing
        self.frame_size = config['frame_size']
        self.buffer_size = config['buffer_size']
        # self.weighting_type = config['weighting_type']
        self.window = None

        # precalculations
        self.overlap = self.frame_size - self.buffer_size
        if config['window_type'] == 'hanning':
            self.window = np.hanning(self.frame_size)
        elif config['window_type'] == 'hamming':
            self.window = np.hamming(self.frame_size)
        elif config['window_type'] == 'rectangle':
            self.window = np.ones(self.frame_size)

        fft_freqs = np.fft.rfftfreq(self.frame_size, 1.0 / self.sample_frequency)
        fft_size = fft_freqs.size
        freq_lower_bound = config['lower_freq']
        freq_upper_bound = config['upper_freq']

        if config['bands_distr'][0] == 'octave':
            oct_freq_lower_bounds, oct_freq_upper_bounds = calc_octave_freq_bounds(
                config['bands_distr'][1], freq_lower_bound, freq_upper_bound
            )
            self.fft_lower_bounds, self.fft_upper_bounds = map_to_fft_bounds(
                oct_freq_lower_bounds, oct_freq_upper_bounds, fft_size
            )
            self.bars = self.fft_lower_bounds.size
        elif config['bands_distr'][0] == 'logspace':
            self.bars = config['bands_distr'][1]
            self.fft_lower_bounds, self.fft_upper_bounds = calc_logspace_fft_bounds(
                self.sample_frequency, self.bars, self.frame_size, freq_lower_bound, freq_upper_bound
            )

        self.adjustment = np.ones(self.bars)
        self.noise_reduction = config['noise_reduction']
        self.amplifier = calc_freq_amplifier(
            self.bars, self.frame_size, freq_lower_bound, freq_upper_bound
        )

        # create buffers
        self.buffer = make_buffer(self.sample_format, self.buffer_size)
        self.frame = np.zeros(self.frame_size, dtype='f')
        self.fft_mags = np.zeros(fft_size, dtype=np.float64)
        self.prev_mags = np.zeros(self.bars, dtype=np.float64)
        self.band_mags = np.ones(self.bars)

        self._callbacks = []
        self._lock = threading.Lock()
        self.__running = threading.Event()
        self.__running.set()
        self.__unblock = threading.Event()
        self.__unblock.set()

    def num_bands(self):
        return self.band_mags.size

    def run(self):
        try:
            while self.__running.is_set():
                self.__unblock.wait()
                with self._lock:
                    fill_buffer(self.connection, self.buffer)
                    filter_signal(self.fft_mags, self.frame, self.buffer, self.overlap, self.buffer_size,
                                  self.window, self.bars, self.fft_lower_bounds, self.fft_upper_bounds,
                                  self.adjustment, self.amplifier,
                                  self.band_mags, self.prev_mags, self.noise_reduction)

                    for callback in self._callbacks:
                        callback()
        except Exception as ex:
            self.disconnect()
            raise ex

    def resume(self):
        self.__unblock.set()

    def pause(self):
        self.__unblock.clear()

    def stop(self):
        self.__unblock.set()
        self.__running.clear()

    def add_callback(self, callback):
        self._callbacks.append(callback)

    def connect(self):
        self.connection = open_connection(**self.pulse_config)
        print('Connection established')

        # jit cache warm-up
        fill_buffer(self.connection, self.buffer)
        filter_signal(self.fft_mags, self.frame, self.buffer, self.overlap, self.buffer_size,
                      self.window, self.bars, self.fft_lower_bounds, self.fft_upper_bounds,
                      self.adjustment, self.amplifier,
                      self.band_mags, self.prev_mags, self.noise_reduction)

    def disconnect(self):
        close_connection(self.connection)
        print('Connection closed')
