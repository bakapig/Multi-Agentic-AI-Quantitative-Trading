"""GARCH(1,1)-t and GJR-GARCH(1,1)-t by maximum likelihood (scipy). Course notation [L6]: e_t = sqrt(h_t) z_t,
h_t = a0 + a1 e_{t-1}^2 + b1 h_{t-1} (GJR adds g*1[e_{t-1}<0] e_{t-1}^2, = APARCH(1,1) with delta=2 [L6 p38]). Returns in percent, zero mean."""
import numpy as np
from scipy.optimize import minimize
from scipy.signal import lfilter
from scipy.special import gammaln


def filter_h(e, a0, a1, b1, g=0.0):
    """h[0..n]: h[t] uses e up to t-1; h[n] is the one-step-ahead forecast."""
    h0 = np.var(e)
    x = np.empty(len(e) + 1)
    x[0] = a0 + (a1 + g / 2) * h0
    x[1:] = a0 + (a1 + g * (e < 0)) * e ** 2
    return lfilter([1.0], [1.0, -b1], x, zi=[b1 * h0])[0]


def _t_ll(e, h, nu):
    return (gammaln((nu + 1) / 2) - gammaln(nu / 2) - 0.5 * np.log(np.pi * (nu - 2)) - 0.5 * np.log(h)
            - (nu + 1) / 2 * np.log1p(e ** 2 / (h * (nu - 2)))).sum()


def _negll(p, e, gjr):
    a0, a1, b1, nu, g = (*p, 0.0) if not gjr else p
    if a1 + g / 2 + b1 >= 0.9999:
        return 1e10
    return -_t_ll(e, filter_h(e, a0, a1, b1, g)[:-1], nu)


def fit(e, start=None, gjr=False):
    """Returns [a0, a1, b1, nu] (GARCH) or [a0, a1, b1, nu, g] (GJR)."""
    v = np.var(e)
    x0 = start if start is not None else ([0.05 * v, 0.03, 0.88, 8.0, 0.08] if gjr else [0.05 * v, 0.07, 0.90, 8.0])
    bnd = [(1e-6, 10 * v), (1e-4 if not gjr else 0.0, 0.4), (0.3, 0.999), (2.5, 60)] + ([(0.0, 0.5)] if gjr else [])
    return minimize(_negll, x0, args=(e, gjr), method="L-BFGS-B", bounds=bnd).x
