"""
Rotary-wing UAV propulsion energy (Zeng et al., "Energy Minimization for
Wireless Communication with Rotary-Wing UAV", IEEE TWC 2019).

Replaces the constant flight-endurance tau_fly of the smoke model: the charging
cadence now emerges from how fast a UAV actually drains its battery while flying
its patrol at speed V, so the queue arrival rate lambda_s is physical.
"""

import math

# --- Default rotary-wing parameters (Zeng 2019, Table I style values) ---
P0 = 79.86     # blade profile power constant [W]
Pind = 88.63   # induced power constant [W]
U_TIP = 120.0  # rotor blade tip speed [m/s]
V0 = 4.03      # mean rotor induced velocity in hover [m/s]
D0 = 0.6       # fuselage drag ratio
RHO = 1.225    # air density [kg/m^3]
S_ROTOR = 0.05 # rotor solidity
A_ROTOR = 0.503  # rotor disc area [m^2]


def propulsion_power(V: float,
                     P0=P0, Pind=Pind, U_tip=U_TIP, v0=V0,
                     d0=D0, rho=RHO, s=S_ROTOR, A=A_ROTOR) -> float:
    """Propulsion power [W] at horizontal speed V [m/s] (Zeng 2019, eq. for P(V)).

    P(V) = P0(1 + 3V^2/U_tip^2)
         + Pind (sqrt(1 + V^4/(4 v0^4)) - V^2/(2 v0^2))^{1/2}
         + 0.5 d0 rho s A V^3
    P(0) = P0 + Pind (hover power).
    """
    blade = P0 * (1.0 + 3.0 * V * V / (U_tip * U_tip))
    induced = Pind * math.sqrt(max(0.0, math.sqrt(1.0 + V**4 / (4.0 * v0**4))
                                   - V * V / (2.0 * v0 * v0)))
    parasite = 0.5 * d0 * rho * s * A * V**3
    return blade + induced + parasite


def hover_power() -> float:
    return P0 + Pind


def endurance(E_max: float, V: float) -> float:
    """Flight time [s] on a full battery E_max [J] cruising at speed V [m/s]."""
    return E_max / propulsion_power(V)


def energy_for_distance(dist: float, V: float) -> float:
    """Energy [J] to fly a horizontal distance dist [m] at speed V [m/s]."""
    if V <= 0:
        return math.inf
    return propulsion_power(V) * (dist / V)


def energy_for_time(t: float, V: float) -> float:
    """Energy [J] to fly for time t [s] at speed V (hover if V=0)."""
    return propulsion_power(V) * t
