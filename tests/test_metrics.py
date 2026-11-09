"""Plan quality metrics are evaluated on the final state.

`_evaluate_metric` used `state.get_value`, which asserts on arithmetic
sub-expressions, so any metric like `(:metric minimize (+ (* 2 (fuel)) 5))`
silently produced no metric at all — the same root cause as the 0.1.4 goal fix,
which switched goal evaluation to `StateEvaluator` but left the metric path
behind.
"""

from pyval import PDDLValidator
from pyval.report_formatter import format_json, format_plain_text
from tests.conftest import write_pddl_files


PROBLEM = """\
(define (problem metric-p1)
  (:domain metric)
  (:objects l1 l2 - loc)
  (:init (at l1) (link l1 l2) (= (fuel l1) 10) (= (distance l1 l2) 4))
  (:goal (at l2))
  (:metric minimize {metric})
)
"""

DOMAIN = """\
(define (domain metric)
  (:requirements :strips :typing :numeric-fluents)
  (:types loc)
  (:predicates (at ?l - loc) (link ?a - loc ?b - loc))
  (:functions (fuel ?l - loc) (distance ?a - loc ?b - loc))
  (:action drive
    :parameters (?from - loc ?to - loc)
    :precondition (and (at ?from) (link ?from ?to)
                       (>= (fuel ?from) (distance ?from ?to)))
    :effect (and (not (at ?from)) (at ?to)
                 (decrease (fuel ?from) (distance ?from ?to))))
)
"""

PLAN = "(drive l1 l2)\n"


def _run(tmp_path, metric: str, domain: str = DOMAIN, problem: str | None = None):
    paths = write_pddl_files(
        tmp_path,
        domain,
        (problem or PROBLEM).replace("{metric}", metric),
        PLAN,
    )
    return PDDLValidator().validate(paths["domain"], paths["problem"], paths["plan"])


def test_plain_fluent_metric(tmp_path):
    result = _run(tmp_path, "(fuel l1)")
    assert result.metric == {
        "type": "minimize",
        "expression": "fuel(l1)",
        "value": 6.0,
    }


def test_arithmetic_metric_is_evaluated(tmp_path):
    """`(+ (* 2 (fuel l1)) 5)` = 2 * 6 + 5 = 17."""
    result = _run(tmp_path, "(+ (* 2 (fuel l1)) 5)")

    assert result.metric is not None
    assert result.metric["value"] == 17.0
    assert "unavailable" not in result.metric


def test_arithmetic_metric_survives_the_report(tmp_path):
    result = _run(tmp_path, "(+ (* 2 (fuel l1)) 5)")
    text = format_plain_text(result)

    assert "Plan metric: minimize" in text
    assert "= 17.0" in text
    assert "could not be evaluated" not in text
    assert format_json(result)["metric"]["value"] == 17.0


def test_action_costs_metric_still_works(tmp_path):
    """`:action-costs` produces MinimizeActionCosts, a final-state metric."""
    domain = """\
(define (domain costs)
  (:requirements :strips :typing :action-costs)
  (:types loc)
  (:predicates (at ?l - loc) (link ?a - loc ?b - loc))
  (:functions (total-cost))
  (:action drive
    :parameters (?from - loc ?to - loc)
    :precondition (and (at ?from) (link ?from ?to))
    :effect (and (not (at ?from)) (at ?to) (increase (total-cost) 3)))
)
"""
    problem = """\
(define (problem costs-p1)
  (:domain costs)
  (:objects l1 l2 - loc)
  (:init (at l1) (link l1 l2) (= (total-cost) 0))
  (:goal (at l2))
  (:metric minimize (total-cost))
)
"""
    paths = write_pddl_files(tmp_path, domain, problem, PLAN)
    result = PDDLValidator().validate(paths["domain"], paths["problem"], paths["plan"])

    assert result.metric["value"] == 3.0
    assert result.metric["expression"] == "action-costs"


def test_unevaluable_metric_is_reported_not_dropped(tmp_path):
    """A metric over a fluent with no value says so instead of vanishing."""
    problem = """\
(define (problem metric-p1)
  (:domain metric)
  (:objects l1 l2 - loc)
  (:init (at l1) (link l1 l2) (= (fuel l1) 10) (= (distance l1 l2) 4))
  (:goal (at l2))
  (:metric minimize (distance l2 l1))
)
"""
    paths = write_pddl_files(tmp_path, DOMAIN, problem, PLAN)
    result = PDDLValidator().validate(paths["domain"], paths["problem"], paths["plan"])

    assert result.metric is not None
    assert result.metric["value"] is None
    assert "UPUsageError" in result.metric["unavailable"]

    text = format_plain_text(result)
    assert "= n/a" in text
    assert "Metric could not be evaluated" in text
