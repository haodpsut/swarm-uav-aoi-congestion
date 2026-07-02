"""
Air-to-ground communication model for data collection.

Gives the time a UAV needs to collect L bits from a sensor at horizontal
distance d, flying at altitude H. Uses a LoS-dominated free-space channel with
a 1 m reference gain beta0; rate = B log2(1 + SNR). This replaces the disk
(instant-collection) model so AoI includes a physical collection dwell.
"""

import math

# --- Default link parameters ---
BETA0_DB = -50.0     # channel gain at 1 m reference distance [dB]
P_TX_DBM = 20.0      # sensor transmit power [dBm] (100 mW)
N0_DBM_HZ = -170.0   # noise PSD [dBm/Hz]
BW = 1e6             # bandwidth [Hz]
ALT = 100.0          # UAV altitude H [m]
PACKET_BITS = 5e6    # L: bits to collect per sensor visit (5 Mb status blob)


def _db2lin(x_db: float) -> float:
    return 10.0 ** (x_db / 10.0)


def rate_bps(d_horiz: float, H: float = ALT,
             beta0_db: float = BETA0_DB, p_tx_dbm: float = P_TX_DBM,
             n0_dbm_hz: float = N0_DBM_HZ, bw: float = BW) -> float:
    """Shannon rate [bit/s] for a ground sensor at horizontal distance d_horiz.

    Link distance = sqrt(H^2 + d^2); free-space power gain = beta0 / dist^2.
    """
    dist = math.sqrt(H * H + d_horiz * d_horiz)
    dist = max(dist, 1.0)
    gain = _db2lin(beta0_db) / (dist * dist)          # linear channel power gain
    p_tx = _db2lin(p_tx_dbm - 30.0)                    # dBm -> W
    noise = _db2lin(n0_dbm_hz - 30.0) * bw             # noise power [W]
    snr = p_tx * gain / noise
    return bw * math.log2(1.0 + snr)


def collect_time(d_horiz: float, L: float = PACKET_BITS, H: float = ALT) -> float:
    """Time [s] to collect L bits from a sensor at horizontal distance d_horiz.

    Evaluated at the UAV's closest-approach distance (best rate); a conservative
    upper bound would integrate along the pass, but closest-approach keeps the
    coverage term interpretable and is standard for hover-and-collect.
    """
    r = rate_bps(d_horiz, H)
    if r <= 0:
        return math.inf
    return L / r
