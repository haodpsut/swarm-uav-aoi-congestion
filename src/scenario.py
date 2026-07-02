"""
Physical scenario (SI units) tying together geometry, energy, comms and the
M/M/c charging queue. This upgrades the semi-analytical smoke: the flight budget
between charges is now derived from the rotary-wing battery drain, and the
patrol revisit time includes a physical collection dwell.

Units: metres, seconds, Joules, m/s.
"""

import math

from energy import propulsion_power, hover_power
from comms import collect_time
from field import patrol_geometry
from queue_model import solve_fixed_point


# --- Default physical scenario ---
DEFAULTS = dict(
    K=60,            # sensors
    L=5000.0,        # field side [m] (5 km)
    H=100.0,         # UAV altitude [m]
    V=12.0,          # cruise speed [m/s] (near min-power)
    E_max=240e3,     # usable battery [J] (~67 Wh)
    E_reserve=0.15,  # keep 15% as safety reserve
    charge_power=500.0,   # charging port power [W] -> tau_charge = E/charge_power
    packet_bits=5e6,      # bits collected per sensor visit
)


def tau_charge_of(E_max, charge_power):
    """Time to refill the usable battery [s]."""
    return E_max / charge_power


def per_uav_cycle(V, E_max, E_reserve, tour_len, n_sensors_group,
                  mean_collect_d, packet_bits):
    """Compute per-UAV physical cycle quantities from real energy/comms.

    tour_len       : patrol tour length for this UAV's sub-field [m]
    n_sensors_group: sensors in the sub-field (collection dwells per loop)
    mean_collect_d : mean horizontal distance at collection [m]
    Returns (t_loop, tau_fly, n_loops): one revisit period [s], the physical
    flight budget between charges [s], and loops per charge.
    """
    P_cruise = propulsion_power(V)
    P_hover = hover_power()

    t_fly_loop = tour_len / V                              # flight time per patrol loop [s]
    t_collect_loop = n_sensors_group * collect_time(mean_collect_d, packet_bits)
    t_loop = t_fly_loop + t_collect_loop                   # one revisit period [s]

    e_fly_loop = P_cruise * t_fly_loop
    e_collect_loop = P_hover * t_collect_loop
    e_loop = e_fly_loop + e_collect_loop                   # energy per loop [J]

    E_usable = E_max * (1.0 - E_reserve)
    n_loops = max(1.0, math.floor(E_usable / e_loop))      # loops between charges
    tau_fly = n_loops * t_loop                             # physical flight budget [s]
    return t_loop, tau_fly, n_loops


def peak_aoi_phys(M, c, mu, tau_fly, t_loop, tau_charge, station_dist, V):
    """Peak AoI = one revisit period + one charging excursion, physical version.

    excursion = round-trip flight to station + queue wait + charge time.
    """
    lam, w, rho, stable = solve_fixed_point(M, c, mu, tau_fly, tau_charge)
    if not stable:
        return math.inf, dict(rho=rho, wq=math.inf, stable=False)
    t_travel = 2.0 * station_dist / V
    excursion = t_travel + w + tau_charge
    aoi = t_loop + excursion
    return aoi, dict(rho=rho, wq=w, stable=True, tau_fly=tau_fly,
                     t_loop=t_loop, excursion=excursion, lam=lam)
