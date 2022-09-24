"""Signal processing and filtering functionality
"""

import ctypes
import numpy as np
from numba import njit, objmode


def shift_frame(frame: np.ndarray, buffer: ctypes.Array, overlap: int, buffer_size: int):
    # frame is updated sequentially with overlap in order for final result
    # to look more smooth when rendered
    frame[:overlap] = frame[buffer_size:]
    frame[overlap:] = buffer


#@njit
def calc_spectrum(fft_mags: np.ndarray, window: np.ndarray, frame: np.ndarray):
    fft_mags[:] = np.abs(np.fft.rfft(window * frame))
    # with objmode():
    #     fft_mags[:] = np.fft.rfft(window * frame)
    # fft_mags[:] = np.abs(fft_mags)


@njit
def calc_psd(fft_mags: np.ndarray, squared_window_sum: np.float64):
    # power spectral density
    fft_mags[:] = np.power(fft_mags * 2., 2) / squared_window_sum

@njit
def log_scale(fft_mags: np.ndarray, fft_freq_weights: np.ndarray):
    fft_mags[:] = 10. * np.log10(fft_mags) + fft_freq_weights


@njit
def linear_scale(fft_mags: np.ndarray, fft_freq_weights: np.ndarray):
    fft_mags[:] *= np.power(10, fft_freq_weights / 20)


@njit
def calc_bands(fft_mags, band_mags, band_freq_weights,
               fft_freq_lower_bounds, fft_freq_upper_bounds):
    for i in range(band_freq_weights.size):
        l = fft_freq_lower_bounds[i]
        u = fft_freq_upper_bounds[i]
        band_mags[i] = np.mean(fft_mags[l:u+1]) + band_freq_weights[i]


def filter_signal(frame: np.ndarray, buffer, overlap: int, buffer_size: int,
                  fft_mags: np.ndarray, window: np.ndarray,
                  squared_window_sum: np.float64,
                  fft_freq_weights: np.ndarray,
                  band_mags: np.ndarray, band_freq_weights: np.ndarray,
                  fft_freq_lower_bounds: np.ndarray, fft_freq_upper_bounds: np.ndarray):
    # apply compostion of filters
    shift_frame(frame, buffer, overlap, buffer_size)
    calc_spectrum(fft_mags, window, frame)
    calc_psd(fft_mags, squared_window_sum)
    log_scale(fft_mags, fft_freq_weights)
    calc_bands(fft_mags, band_mags, band_freq_weights,
               fft_freq_lower_bounds, fft_freq_upper_bounds)


@njit
def calc_freq_weights(frequencies: np.ndarray, weighting_type: str) -> np.ndarray:
    if weighting_type == 'A':
        a = np.power(12194.0, 2) * np.power(frequencies, 4)
        b = (np.power(frequencies, 2) + np.power(20.6, 2))
        c = (np.power(frequencies, 2) + np.power(107.7, 2))
        d = (np.power(frequencies, 2) + np.power(737.9, 2))
        e = (np.power(frequencies, 2) + np.power(12194.0, 2))
        R_A = a / (b * np.sqrt(c * d) * e)
        A = 20 * np.log10(R_A) + 2.0
        return A
    elif weighting_type == 'C':
        a = np.power(12194.0, 2) * np.power(frequencies, 2)
        b = np.power(frequencies, 2) + np.power(20.6, 2)
        c = np.power(frequencies, 2) + np.power(12194.0, 2)
        R_C = (a / (b * c))
        C = 20 * np.log10(R_C) + 0.06
        return C
    elif weighting_type == 'Z':
        return np.ones(frequencies.shape)


def calc_uniform_freq_bounds(fft_size: int, num_bands: int) -> tuple[np.ndarray, np.ndarray]:
    split = np.round(np.linspace(0, fft_size - 1, num_bands + 1))
    lower_bounds = []
    upper_bounds = []
    for i in range(split.size - 1):
        lower_bounds.append(split[i])
        upper_bounds.append(split[i + 1])

    return np.array(lower_bounds, dtype=np.int64), np.array(upper_bounds, dtype=np.int64)


def calc_octave_freq_bounds(fraction=3, g=2, limits=[12, 20000]) -> tuple[np.ndarray, np.ndarray]:
    # https://law.resource.org/pub/us/cfr/ibr/002/ansi.s1.11.2004.pdf
    # https://apmr.matelys.com/Standards/OctaveBands.html

    # fraction: bandwidth for octave fraction in format 1/`fraction`-octave
    # e.g. 1/3-octave => `fraction` = 3, 2/3-octave => `fraction` = 3/2
    # g: Octave ratio

    # Reference frequency
    fr = 1000

    if fraction % 2:
        center_idx = np.round(
            (fraction * np.log(limits[0] / fr) + 30 * np.log(g)) / np.log(g)
        )
    else:
        center_idx = np.round(
            (2 * fraction * np.log(limits[0] / fr) + 59 * np.log(g)) / (2 * np.log(g))
        )

    def _band_edge(g, fraction):
        return g ** (1 / (2 * fraction))

    def _ratio(g, center_idx, fraction):
        if fraction % 2:
            return g ** ((center_idx - 30) / fraction)
        else:
            return g ** ((2 * center_idx - 59) / (2 * fraction))

    center_freq = _ratio(g, center_idx, fraction) * fr

    nth_freq = 0
    while nth_freq * _band_edge(g, fraction) < limits[1]:
        center_idx += 1
        nth_freq = _ratio(g, center_idx, fraction) * fr
        center_freq = np.append(center_freq, nth_freq)

    lower_bounds = center_freq / _band_edge(g, fraction)
    upper_bounds = center_freq * _band_edge(g, fraction)

    return lower_bounds, upper_bounds


def map_to_fft_freq_bounds(oct_freq_lower_bounds, oct_freq_upper_bounds,
                           fft_size) -> tuple[np.ndarray, np.ndarray]:
    num_splits = oct_freq_lower_bounds.size
    lower_bounds = np.zeros(num_splits, np.int64)
    upper_bounds = np.zeros(num_splits, np.int64)
    max_upper_bound = fft_size - 1
    ratio = fft_size / max(oct_freq_upper_bounds)
    for i in range(num_splits):
        lower_bounds[i] = np.clip(np.round(oct_freq_lower_bounds[i] * ratio), 0, max_upper_bound)
        upper_bounds[i] = np.clip(np.round(oct_freq_upper_bounds[i] * ratio), 0, max_upper_bound)

    return lower_bounds, upper_bounds
