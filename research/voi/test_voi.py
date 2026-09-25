"""Tests for voi_screen.py. Run: python3 research/voi/test_voi.py"""
import math
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import voi_screen as v  # noqa: E402


def test_gain_matches_monte_carlo():
    rng = np.random.default_rng(0)
    for mu, sd, k in ((0.0, 0.02, 1), (-0.01, 0.03, 2), (0.02, 0.01, 1)):
        m = rng.normal(mu, sd, 400_000)
        mc = np.maximum(m - k * v.C1, 0).mean() - max(mu - k * v.C1, 0)
        assert abs(v.gain(mu, sd, k) - mc) < 3e-4, (mu, sd, k)


def test_gain_nonnegative_and_zero_without_uncertainty():
    assert v.gain(0.01, 0.0, 1) == 0.0
    for mu in (-0.05, 0.0, 0.05):
        assert v.gain(mu, 0.02, 1) >= 0


def test_evsi_never_exceeds_evpi():
    for name, fn in v.CANDIDATES.items():
        for days in v.HORIZONS.values():
            for s in v.SCEN:
                evpi, evsi, _ = fn(s, days)
                assert evsi <= evpi + 1e-12, (name, s, days)


def test_no_data_means_no_evsi():
    assert v.prepost_sd(0.2, None) == 0.0
    assert v.prepost_sd(0.2, math.inf) == 0.0
    # more precise data -> preposterior sd approaches prior sd
    assert v.prepost_sd(0.2, 1e-6) > 0.199


def test_mde_shrinks_with_days_and_cluster_size():
    assert v.mde(60, 0.1, 0.3, 3) < v.mde(20, 0.1, 0.3, 3)
    assert v.mde(60, 0.1, 0.3, 10) < v.mde(60, 0.1, 0.3, 1)
    assert v.mde(2, 0.1, 0.3, 3) == float("inf")
    d = v.days_to(0.02, 0.1, 0.3, 3)
    assert abs(v.mde(d, 0.1, 0.3, 3) - 0.02) < 1e-9


def test_ledger_params_on_real_file():
    p = v.ledger_params()
    assert p["n_assets"] == 19 and p["bars"] == 720
    assert 0.02 < p["link_daily_sd"] < 0.08
    assert 0.0 < p["sigma_x"] < 0.5 and -0.1 < p["rho"] < 1.0


def test_ledger_params_recovers_planted_structure(tmp=None):
    """Synthetic file: common factor + idiosyncratic noise with known rho."""
    import json
    import tempfile
    rng = np.random.default_rng(1)
    n, k = 721, 20
    f = rng.normal(0, 0.02, n)
    rets = {f"A{i:02d}": f + rng.normal(0, 0.02, n) for i in range(k - 1)}
    rets["LINKUSD"] = rng.normal(0, 0.03, n)
    d = {a: {"1440": [[t, 0, 0, 0, float(np.exp(np.cumsum(r))[t]), 0] for t in range(n)]}
         for a, r in rets.items()}
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as fh:
        json.dump(d, fh)
    p = v.ledger_params(fh.name)
    os.unlink(fh.name)
    # excess = f + e_i - link: cov = var(f)+var(link) = 13e-4 per day; var = 17e-4 -> rho ~0.76
    assert abs(p["rho"] - 13 / 17) < 0.08, p["rho"]
    assert abs(p["sigma_x"] - math.sqrt(17e-4 * 3)) < 0.01, p["sigma_x"]


if __name__ == "__main__":
    tests = [(k, f) for k, f in globals().items() if k.startswith("test_")]
    ok = 0
    for k, f in tests:
        try:
            f()
            print("ok ", k)
            ok += 1
        except AssertionError as e:
            print("FAIL", k, e)
    print(f"{ok}/{len(tests)} passed")
    sys.exit(0 if ok == len(tests) else 1)
