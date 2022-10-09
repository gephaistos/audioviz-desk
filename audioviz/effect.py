"""Additional effects for rendered visuals
"""


from numba import njit


@njit
def monstercat(band_mags, base=2.0):
    # rebalance bars heights to follow exponent curve shape
    for bar in range(band_mags.size):
        for prev_bar in range(bar - 1, -1, -1):
            distance = bar - prev_bar
            band_mags[prev_bar] = max(band_mags[bar] / pow(base, distance), band_mags[prev_bar])
        for next_bar in range(bar + 1, band_mags.size):
            distance = next_bar - bar
            band_mags[next_bar] = max(band_mags[bar] / pow(base, distance), band_mags[next_bar])
