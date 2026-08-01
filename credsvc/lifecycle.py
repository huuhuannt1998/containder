"""Three-layer authority lifecycle: credential, session, and command effect.

Why this module exists
----------------------
The pilot reported mechanism ablations that were **not identified by its harness**: the
`legacy`, `no_session` and `no_cleanup` arms mapped onto a single activity predicate, so three
labels named one arm and their per-seed output series were byte-identical. The claim that
"removing session enforcement or command cleanup returns the feeder to no recovery, so each
mechanism is necessary" read a relabelling as a result, and it was withdrawn.

The defect was in the model, not the measurement: a single boolean "is the credential valid"
cannot distinguish three layers that expire at different times. This module supplies the missing
state machine. Retained authority is decomposed into

    BR_auth = (T_cred, T_sess, T_cmd)

per the revision's requirement that a single maximum not hide which containment layer failed:

* **T_cred** -- how long the credential itself authorizes *new sessions*.
* **T_sess** -- how long an *already established* session keeps accepting new commands. A
  session opened under a valid credential does not necessarily close when that credential
  expires; whether it does is the session-enforcement mechanism.
* **T_cmd** -- how long an *already issued* control keeps acting on the feeder. A scheduled
  DERControl with a duration outlives the session that issued it unless something cancels it;
  whether anything does is the command-cleanup mechanism.

Because the three layers end at different times, the four mechanism arms produce four different
*physical* timelines, which is what :mod:`experiments.run_mechanism_ablation` measures on the
feeder. That is the ablation the pilot could not perform.

The same state machine expresses the local-denylist baselines, because a denylist is simply a
response event at detection time whose reach across the three layers is exactly the question:
denying an identity refuses future authorization, but on its own it neither closes an open
session nor retracts an issued control.
"""
from __future__ import annotations

import math
from dataclasses import dataclass

#: Response reach: which of the three layers an operator's action actually terminates.
RESPONSES = {
    # name                 new sessions  open session  issued commands
    "none": (False, False, False),
    "denylist": (True, False, False),
    "denylist+session": (True, True, False),
    "denylist+session+cancel": (True, True, True),
}


@dataclass(frozen=True)
class LifecyclePolicy:
    """A credential-lifecycle configuration. Times in seconds from the start of the horizon."""
    name: str
    #: Credential lifetime. math.inf models the long-lived baseline certificate.
    ttl_s: float
    #: Does the enforcement point revalidate the credential on every command, closing or
    #: refusing an established session once the credential expires?
    enforce_session: bool
    #: Does expiry (or denial) cancel already-issued controls and restore a safe profile?
    enforce_cleanup: bool
    #: How long a cached session keeps accepting commands when session enforcement is absent.
    session_max_age_s: float = 24 * 3600.0
    #: Duration of each issued DERControl; the adversary re-issues at this cadence.
    command_duration_s: float = 900.0
    #: Delay between a cancellation decision and the control ceasing to act on the feeder.
    cleanup_latency_s: float = 60.0

    @property
    def enforces_any(self) -> bool:
        return self.enforce_session or self.enforce_cleanup


@dataclass(frozen=True)
class Incident:
    """One compromise, with the operator's detection and response."""
    #: When the adversary obtains the credential and opens its session.
    t_compromise_s: float
    #: When the operator detects the compromise; math.inf if never.
    t_detect_s: float = math.inf
    #: Which layers the operator's response reaches. Key of :data:`RESPONSES`.
    response: str = "none"
    #: When the credential in the adversary's hands was issued. Defaults to the compromise
    #: instant, i.e. the worst case in which the adversary holds a whole fresh lifetime.
    t_issue_s: float = None

    def issue_time(self) -> float:
        return self.t_compromise_s if self.t_issue_s is None else self.t_issue_s


def _session_accepts(policy: LifecyclePolicy, incident: Incident, t: float) -> bool:
    """Whether the established session accepts a *new* command at time ``t``.

    This is the session layer. With enforcement the credential is revalidated on every command,
    so the session cannot outlive expiry. Without it the session runs to its own age limit and
    credential expiry is invisible to it. That difference is what the pilot harness collapsed.
    """
    _, deny_session, _ = RESPONSES[incident.response]
    if t < incident.t_compromise_s:
        return False
    if policy.enforce_session:
        if t >= incident.issue_time() + policy.ttl_s:
            return False
    elif t >= incident.t_compromise_s + policy.session_max_age_s:
        return False
    if deny_session and t >= incident.t_detect_s:
        return False
    return True


def _cleanup_running(policy: LifecyclePolicy, incident: Incident, t: float) -> bool:
    """Whether the cleanup sweep is cancelling already-issued controls at time ``t``."""
    _, _, cancel_cmds = RESPONSES[incident.response]
    if policy.enforce_cleanup and t >= incident.issue_time() + policy.ttl_s:
        return True
    if cancel_cmds and t >= incident.t_detect_s:
        return True
    return False


def simulate(policy: LifecyclePolicy, incident: Incident,
             horizon_s: float, step_s: float) -> dict:
    """Step the three layers forward and return the effect timeline plus the BR_auth vector.

    The simulation, not a closed form, is the source of truth, because the layers interact: a
    cleanup sweep that cancels a control does **not** stop an adversary whose session still
    accepts commands from immediately issuing another. That interaction is the reason neither
    mechanism contains on its own, and a closed form that treats cleanup as a terminal event
    silently asserts the conclusion instead of measuring it.
    """
    n = int(round(horizon_s / step_s))
    active_until = None          # absolute time at which the acting control lapses
    effect = []
    n_issued = 0
    t_last_accepted = None
    t_last_session_open = None   # last step at which the session *would* accept a command
    for k in range(n):
        t = k * step_s
        if _session_accepts(policy, incident, t):
            t_last_session_open = t
        # 1. Cleanup sweep cancels a control whose authority has lapsed. The cancellation
        #    takes cleanup_latency_s to reach the feeder.
        if active_until is not None and _cleanup_running(policy, incident, t):
            active_until = min(active_until, t + policy.cleanup_latency_s)
        # 2. The adversary refreshes its control whenever the session will accept one and no
        #    control is currently acting.
        if _session_accepts(policy, incident, t) and (active_until is None or active_until <= t):
            active_until = t + policy.command_duration_s
            n_issued += 1
            t_last_accepted = t
        effect.append(active_until is not None and t < active_until)

    t0 = incident.t_compromise_s
    t_exp = incident.issue_time() + policy.ttl_s
    deny_new, _, _ = RESPONSES[incident.response]
    cred_end = min(t_exp, incident.t_detect_s) if deny_new else t_exp

    # Observed ends, read off the simulation rather than assumed. The session layer's end is
    # the last step at which it *would* have accepted a command, not the last step at which the
    # adversary happened to issue one: an adversary holding a 15-minute control has no reason to
    # re-issue every minute, and reading its cadence would understate the authority it retains.
    sess_end = (t_last_session_open + step_s) if t_last_session_open is not None else t0
    idx = [k for k, e in enumerate(effect) if e]
    cmd_end = (idx[-1] + 1) * step_s if idx else t0

    return {
        "effect": effect,
        "n_commands_accepted": n_issued,
        "t_cred_end": cred_end,
        "t_sess_end": sess_end,
        "t_cmd_end": cmd_end,
        "t_expiry": t_exp,
        "t_detect": incident.t_detect_s,
        # Retained-authority durations from the compromise: the BR_auth vector the manuscript
        # reports in place of a single maximum, which would hide which layer failed.
        "T_cred": max(0.0, cred_end - t0),
        "T_sess": max(0.0, sess_end - t0),
        "T_cmd": max(0.0, cmd_end - t0),
        "post_expiry_effect_s": max(0.0, cmd_end - t_exp),
    }


def effect_timeline(policy: LifecyclePolicy, incident: Incident,
                    horizon_s: float, step_s: float) -> "list[bool]":
    """Per-step indicator of whether the adversarial control is acting on the feeder.

    This is the bridge to the physical experiment: the feeder harness applies the adversarial
    operating point exactly on the steps this returns True and legitimate operation on the
    rest, so two arms differing only in a lifecycle mechanism produce two different voltage
    time series.
    """
    return simulate(policy, incident, horizon_s, step_s)["effect"]


def authority_bounds(policy: LifecyclePolicy, incident: Incident,
                     horizon_s: float = 3600.0, step_s: float = 60.0) -> dict:
    """(T_cred, T_sess, T_cmd) for one arm, without retaining the timeline."""
    out = simulate(policy, incident, horizon_s, step_s)
    out.pop("effect")
    return out


#: The four mechanism arms of the ablation, at a common credential lifetime.
def ablation_arms(ttl_s: float, **kw) -> "dict[str, LifecyclePolicy]":
    return {
        "S0": LifecyclePolicy("S0 no session enforcement, no cleanup", ttl_s, False, False, **kw),
        "S1": LifecyclePolicy("S1 session enforcement only", ttl_s, True, False, **kw),
        "S2": LifecyclePolicy("S2 command cleanup only", ttl_s, False, True, **kw),
        "S3": LifecyclePolicy("S3 full CONTAINDER", ttl_s, True, True, **kw),
    }


def legacy_policy(**kw) -> LifecyclePolicy:
    """The baseline: a long-lived certificate with neither mechanism."""
    return LifecyclePolicy("legacy long-lived", math.inf, False, False, **kw)
