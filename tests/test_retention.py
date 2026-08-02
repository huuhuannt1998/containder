"""The corrected retention closed forms must match simulation, and must differ from T/p.

The manuscript previously reported T/p as the containment-latency figure of merit for every
compromise class. These tests pin the two ways that is wrong.
"""
import math

import pytest

from pkimodel import retention as R

TTL = 6 * 3600.0        # a six-hour operational credential


@pytest.mark.parametrize("p", [0.2, 0.5, 0.9, 1.0])
@pytest.mark.parametrize("arrival", ["uniform", "immediate"])
def test_persistent_closed_form_matches_simulation(p, arrival):
    model = R.persistent_compromise(TTL, p, arrival=arrival)
    sim = R.simulate_persistent(TTL, p, arrival=arrival, n=100_000)
    assert model.expected == pytest.approx(sim, rel=0.02), (
        f"closed form {model.formula} = {model.expected:.1f}s but simulation gives {sim:.1f}s")


@pytest.mark.parametrize("arrival", ["uniform", "immediate"])
def test_copied_key_closed_form_matches_simulation(arrival):
    model = R.copied_key(TTL, arrival=arrival)
    sim = R.simulate_copied(TTL, arrival=arrival, n=100_000)
    assert model.expected == pytest.approx(sim, rel=0.02)


@pytest.mark.parametrize("p", [0.1, 0.3, 0.6])
def test_copied_key_does_not_depend_on_detection_probability(p):
    """Fresh-key rotation contains a copied key whatever attestation does.

    This is the first error in the old T/p framing: it credits attestation with a bound that
    key rotation already supplies, and inflates the copied-key figure by 1/p.
    """
    model = R.copied_key(TTL)
    assert model.depends_on_detection is False
    t_over_p = TTL / p
    assert model.expected < t_over_p
    assert model.expected == pytest.approx(TTL / 2.0)


@pytest.mark.parametrize("p", [0.1, 0.25, 0.5, 0.75])
def test_uniform_arrival_is_strictly_shorter_than_T_over_p(p):
    """The second error: T/p assumes the compromise lands right after an issuance.

    A compromise arriving uniformly in the epoch is expected to be contained half a lifetime
    sooner, so T/p overstates retention for the realistic arrival.
    """
    uniform = R.persistent_compromise(TTL, p, arrival="uniform").expected
    immediate = R.persistent_compromise(TTL, p, arrival="immediate").expected
    assert immediate == pytest.approx(TTL / p)
    assert uniform == pytest.approx(TTL * (1.0 / p - 0.5))
    assert uniform == pytest.approx(immediate - TTL / 2.0)
    assert uniform < immediate


def test_perfect_detection_bounds_persistent_at_one_epoch():
    """With p = 1 the adversary loses authority at the first renewal, not before."""
    assert R.persistent_compromise(TTL, 1.0, arrival="immediate").expected == pytest.approx(TTL)
    assert R.persistent_compromise(TTL, 1.0, arrival="uniform").expected == pytest.approx(TTL / 2)


def test_session_and_command_classes_are_not_bounded_by_credential_expiry():
    """The two layers whose bound is a mechanism, not a lifetime."""
    sess = R.stolen_session(session_max_age=24 * 3600.0, revalidation_interval=60.0)
    assert sess.expected == pytest.approx(60.0)
    cmd = R.persistent_command(command_duration=900.0, cancel_latency=60.0)
    assert cmd.expected == pytest.approx(60.0)
    # Without a revalidation or cancellation mechanism the bound reverts to the long path.
    assert R.stolen_session(24 * 3600.0, math.inf).expected == pytest.approx(24 * 3600.0)
    assert R.persistent_command(900.0, math.inf).expected == pytest.approx(900.0)


def test_undetectable_class_is_outside_the_guarantee():
    m = R.undetectable_compromise(TTL, horizon=30 * 24 * 3600.0)
    assert m.worst_case == math.inf
    assert m.depends_on_detection is False
