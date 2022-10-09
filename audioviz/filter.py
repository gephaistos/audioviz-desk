"""Signal processing and filtering functionality
"""

import ctypes
import numpy as np
from numba import njit


def shift_frame(frame: np.ndarray, buffer: ctypes.Array, overlap: int, buffer_size: int):
    frame[:overlap] = frame[buffer_size:]
    frame[overlap:] = buffer


#@njit
def calc_spectrum(fft_mags: np.ndarray, window: np.ndarray, frame: np.ndarray):
    fft_mags[:] = np.abs(np.fft.rfft(window * frame))
    # with numba.objmode():
    #     fft_mags[:] = np.fft.rfft(window * frame)
    # fft_mags[:] = np.abs(fft_mags)


@njit
def calc_psd(fft_mags: np.ndarray, squared_window_sum: np.float64):
    # power spectral density
    fft_mags[:] = np.power(fft_mags * 2., 2) / squared_window_sum


@njit
def log_scale(fft_mags: np.ndarray, fft_weights: np.ndarray):
    fft_mags[:] = 10. * np.log10(fft_mags) + fft_weights


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


@njit
def calc_bands(fft_mags, band_mags, band_weights,
               fft_lower_bounds, fft_upper_bounds):
    for i in range(band_weights.size):
        l = fft_lower_bounds[i]
        u = fft_upper_bounds[i]
        band_mags[i] = np.mean(fft_mags[l:u+1]) + band_weights[i]


def octave_filter(frame: np.ndarray, buffer, overlap: int, buffer_size: int,
                  fft_mags: np.ndarray, window: np.ndarray,
                  squared_window_sum: np.float64,
                  fft_weights: np.ndarray,
                  band_mags: np.ndarray, band_weights: np.ndarray,
                  fft_lower_bounds: np.ndarray, fft_upper_bounds: np.ndarray):
    # apply compostion of filters
    shift_frame(frame, buffer, overlap, buffer_size)
    calc_spectrum(fft_mags, window, frame)
    calc_psd(fft_mags, squared_window_sum)
    log_scale(fft_mags, fft_weights)
    calc_bands(fft_mags, band_mags, band_weights,
               fft_lower_bounds, fft_upper_bounds)


def calc_octave_freq_bounds(fraction=3, g=2, freq_lower_bound=12, freq_upper_bound=20000) -> tuple[np.ndarray, np.ndarray]:
    # https://law.resource.org/pub/us/cfr/ibr/002/ansi.s1.11.2004.pdf
    # https://apmr.matelys.com/Standards/OctaveBands.html

    # fraction: bandwidth for octave fraction in format 1/`fraction`-octave
    # e.g. 1/3-octave => `fraction` = 3, 2/3-octave => `fraction` = 3/2
    # g: Octave ratio

    # Reference frequency
    fr = 1000

    if fraction % 2:
        center_idx = np.round(
            (fraction * np.log(freq_lower_bound / fr) + 30 * np.log(g)) / np.log(g)
        )
    else:
        center_idx = np.round(
            (2 * fraction * np.log(freq_lower_bound / fr) + 59 * np.log(g)) / (2 * np.log(g))
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
    while nth_freq * _band_edge(g, fraction) < freq_upper_bound:
        center_idx += 1
        nth_freq = _ratio(g, center_idx, fraction) * fr
        center_freq = np.append(center_freq, nth_freq)

    lower_bounds = center_freq / _band_edge(g, fraction)
    upper_bounds = center_freq * _band_edge(g, fraction)

    return lower_bounds, upper_bounds


def map_to_fft_bounds(oct_freq_lower_bounds, oct_freq_upper_bounds,
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


def calc_logspace_fft_bounds(sample_frequency, bars, frame_size,
                             freq_lower_bound=12, freq_upper_bound=20000) -> tuple[np.ndarray, np.ndarray]:
    fft_lower_bounds = np.zeros(bars + 1, dtype=np.int32)
    fft_upper_bounds = np.zeros(bars + 1, dtype=np.int32)

    freqconst = np.log10(freq_lower_bound / freq_upper_bound) / (1 / (bars + 1) - 1)
    fc = np.zeros(bars + 1, dtype=np.float32)
    for n in range(bars + 1):
        fc[n] = freq_upper_bound * np.power(
            10, freqconst * (-1) + (((n + 1) / (bars + 1)) * freqconst)
        )
        fc[n] = fc[n] / (sample_frequency / 2)

        fft_lower_bounds[n] = fc[n] * (frame_size /2)
        if (n != 0):
            fft_upper_bounds[n - 1] = fft_lower_bounds[n] - 1

            if (fft_lower_bounds[n] <= fft_lower_bounds[n - 1]):
                fft_lower_bounds[n] = fft_lower_bounds[n - 1] + 1
            fft_upper_bounds[n - 1] = fft_lower_bounds[n] - 1

    return fft_lower_bounds, fft_upper_bounds


def calc_freq_amplifier(bars, frame_size, freq_lower_bound=12, freq_upper_bound=12000) -> np.ndarray:
    amplifier = np.zeros(bars + 1, dtype=np.float64)

    bars_third = int(np.round(bars / 3))
    amplifier[:bars_third] = np.logspace(np.log2(2), np.log2(1), bars_third, base=2)
    amplifier[bars_third:2 * bars_third] = np.logspace(np.log2(1), np.log2(0.6), bars_third, base=2)
    amplifier[2 * bars_third:] = np.logspace(np.log2(0.6), np.log2(0.3), bars + 1 - 2 * bars_third, base=2)

    freqconst = np.log10(freq_lower_bound / freq_upper_bound) / (1 / (bars + 1) - 1)
    fc = np.zeros(bars + 1, dtype=np.float32)
    for n in range(bars + 1):
        fc[n] = freq_upper_bound * np.power(
            10, freqconst * (-1) + (((n + 1) / (bars + 1)) * freqconst)
        )
        amplifier[n] = fc[n] * amplifier[n] / np.log2(frame_size)

    return amplifier


def logspace_filter(fft_mags, frame, buffer, overlap, buffer_size, window,
                    bars, fft_lower_bounds, fft_upper_bounds, adjustment, amplifier,
                    band_mags, cava_mem, noise_reduction):
    shift_frame(frame, buffer, overlap, buffer_size)
    calc_spectrum(fft_mags, window, frame)
    gather_energy(fft_mags, bars, fft_lower_bounds, fft_upper_bounds, adjustment, amplifier,
                  band_mags, cava_mem, noise_reduction)


@njit
def gather_energy(fft_mags, bars, fft_lower_bounds, fft_upper_bounds, adjustment, amplifier,
                  band_mags, prev_mags, noise_reduction):
    for n in range(bars):
        energy = 0
        for i in range(fft_lower_bounds[n], fft_upper_bounds[n] + 1):
            energy += fft_mags[i]

        energy /= fft_upper_bounds[n] - fft_lower_bounds[n] + 1
        energy *= amplifier[n]
        band_mags[n] = energy

    band_mags *= adjustment

    excess = 0
    for n in range(bars):
        band_mags[n] = prev_mags[n] * noise_reduction + band_mags[n]
        prev_mags[n] = band_mags[n]

        diff = 300 - band_mags[n]
        if (diff < 0):
            diff = 0
        div = 1 / (diff + 1)
        prev_mags[n] = prev_mags[n] * (1 - div / 20)

        if (band_mags[n] > 300):
            excess = 1
        band_mags[n] /= 300

    if excess:
        adjustment *= 1 - 0.01
    else:
        adjustment *= 1 + 0.001
