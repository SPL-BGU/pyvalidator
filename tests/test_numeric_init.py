"""Phase-1 warnings for numeric fluent instances that :init never assigns.

PDDL defines no default for a numeric fluent, and the simulator has no value
for an instance that :init leaves out: reading one raises ``UPUsageError``.
These tests pin the per-instance coverage of that warning (the check used to be
per declared name, so initialising ``(fuel t1)`` silenced the warning for
``(fuel t2)`` entirely) and the absence of the old, false "defaults to 0" claim.
"""

from pyval.syntax_checker import check_syntax
from tests.conftest import write_pddl_files


NUMERIC_DOMAIN = """\
(define (domain numinit)
  (:requirements :strips :typing :numeric-fluents)
  (:types truck loc)
  (:predicates (at ?t - truck ?l - loc) (link ?a - loc ?b - loc))
  (:functions (fuel ?t - truck) (distance ?a - loc ?b - loc))
  (:action drive
    :parameters (?t - truck ?from - loc ?to - loc)
    :precondition (and (at ?t ?from) (link ?from ?to)
                       (>= (fuel ?t) (distance ?from ?to)))
    :effect (and (not (at ?t ?from)) (at ?t ?to)
                 (decrease (fuel ?t) (distance ?from ?to))))
)
"""


def _problem(init: str) -> str:
    return f"""\
(define (problem numinit-p1)
  (:domain numinit)
  (:objects t1 t2 - truck l1 l2 - loc)
  (:init (at t1 l1) (at t2 l1) (link l1 l2) (= (distance l1 l2) 10)
    {init}
  )
  (:goal (at t1 l2))
)
"""


def _warnings(tmp_path, init: str) -> list[str]:
    paths = write_pddl_files(tmp_path, NUMERIC_DOMAIN, _problem(init))
    result, problem = check_syntax(paths["domain"], paths["problem"])
    assert result["status"] == "PASS"
    assert problem is not None
    return result["warnings"]


def test_partial_initialisation_names_the_missing_instance(tmp_path):
    """`(= (fuel t1) 50)` says nothing about `fuel(t2)` — name it explicitly."""
    warnings = _warnings(tmp_path, "(= (fuel t1) 50)")

    fuel = [w for w in warnings if "'fuel'" in w]
    assert len(fuel) == 1, warnings
    message = fuel[0]
    assert "fuel(t2)" in message
    assert "fuel(t1)" not in message  # the initialised instance is not reported
    assert "1 of its 2 ground instances" in message
    # Repair hint must be valid PDDL: `(= (fuel t2) <value>)`, not `(= fuel(t2) ...)`
    assert "Add (= (fuel t2) <value>) to :init." in message


def test_warning_does_not_claim_a_default_of_zero(tmp_path):
    """The old text said the value "defaults to 0" — it does not; it is absent."""
    for warning in _warnings(tmp_path, "(= (fuel t1) 50)"):
        assert "defaults to 0" not in warning
        assert "assigns no default" in warning


def test_fully_initialised_function_is_not_reported(tmp_path):
    warnings = _warnings(
        tmp_path, "(= (fuel t1) 50) (= (fuel t2) 20)"
    )
    assert not [w for w in warnings if "'fuel'" in w]


def test_every_instance_missing_is_reported_once(tmp_path):
    warnings = _warnings(tmp_path, "(= (distance l1 l2) 10) (= (fuel t1) 1) (= (fuel t2) 1)")
    distance = [w for w in warnings if "'distance'" in w]
    assert len(distance) == 1
    assert "3 of its 4 ground instances" in distance[0]
    assert "distance(l1, l2)" not in distance[0]
    # Comma-separated UPF rendering must not survive into the PDDL repair hint
    assert "Add (= (distance l1 l1) <value>) to :init." in distance[0]


def test_zero_arity_function_without_init_is_reported(tmp_path):
    domain = """\
(define (domain nularity)
  (:requirements :strips :numeric-fluents)
  (:predicates (done))
  (:functions (total-cost))
  (:action noop :parameters () :precondition (done) :effect (increase (total-cost) 1))
)
"""
    problem = """\
(define (problem nularity-p1)
  (:domain nularity)
  (:init (done))
  (:goal (done))
)
"""
    paths = write_pddl_files(tmp_path, domain, problem)
    result, _ = check_syntax(paths["domain"], paths["problem"])
    message = [w for w in result["warnings"] if "'total-cost'" in w]
    assert len(message) == 1
    assert "has no initial value: total-cost" in message[0]
    assert "Add (= total-cost <value>) to :init." in message[0]


def test_long_missing_list_is_summarised(tmp_path):
    """A function over many objects lists a few instances, then the remainder."""
    domain = """\
(define (domain many)
  (:requirements :strips :typing :numeric-fluents)
  (:types thing)
  (:predicates (p ?x - thing))
  (:functions (cost ?x - thing))
  (:action noop :parameters (?x - thing) :precondition (p ?x)
    :effect (decrease (cost ?x) 1))
)
"""
    objects = " ".join(f"o{i}" for i in range(10))
    problem = f"""\
(define (problem many-p1)
  (:domain many)
  (:objects {objects} - thing)
  (:init (p o0))
  (:goal (p o0))
)
"""
    paths = write_pddl_files(tmp_path, domain, problem)
    result, _ = check_syntax(paths["domain"], paths["problem"])
    message = [w for w in result["warnings"] if "'cost'" in w][0]
    assert "10 of its 10 ground instances" in message
    assert "4 more)" in message


def test_huge_ground_space_is_not_enumerated(tmp_path):
    """Two 17-object parameters exceed the enumeration bound; warn instead."""
    domain = """\
(define (domain huge)
  (:requirements :strips :typing :numeric-fluents)
  (:types thing)
  (:predicates (p ?x - thing ?y - thing))
  (:functions (cost ?x - thing ?y - thing))
  (:action noop :parameters (?x - thing ?y - thing) :precondition (p ?x ?y)
    :effect (decrease (cost ?x ?y) 1))
)
"""
    objects = " ".join(f"o{i}" for i in range(17))
    problem = f"""\
(define (problem huge-p1)
  (:domain huge)
  (:objects {objects} - thing)
  (:init (p o0 o0))
  (:goal (p o0 o0))
)
"""
    paths = write_pddl_files(tmp_path, domain, problem)
    result, _ = check_syntax(paths["domain"], paths["problem"])
    message = [w for w in result["warnings"] if "'cost'" in w][0]
    assert "more than 250 ground instances" in message
    assert "No default value is assumed" in message
