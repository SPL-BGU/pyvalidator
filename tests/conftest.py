"""Shared test fixtures for PyVAL tests."""

import pytest


# ---------------------------------------------------------------------------
# Classical domain: simple blocksworld
# ---------------------------------------------------------------------------

BLOCKSWORLD_DOMAIN = """\
(define (domain blocksworld)
  (:requirements :strips :typing)
  (:types block)
  (:predicates
    (on ?x - block ?y - block)
    (ontable ?x - block)
    (clear ?x - block)
    (holding ?x - block)
    (arm-empty)
  )

  (:action pick-up
    :parameters (?x - block)
    :precondition (and (clear ?x) (ontable ?x) (arm-empty))
    :effect (and (not (ontable ?x)) (not (clear ?x)) (not (arm-empty)) (holding ?x))
  )

  (:action put-down
    :parameters (?x - block)
    :precondition (holding ?x)
    :effect (and (not (holding ?x)) (arm-empty) (ontable ?x) (clear ?x))
  )

  (:action stack
    :parameters (?x - block ?y - block)
    :precondition (and (holding ?x) (clear ?y))
    :effect (and (not (holding ?x)) (not (clear ?y)) (clear ?x) (arm-empty) (on ?x ?y))
  )

  (:action unstack
    :parameters (?x - block ?y - block)
    :precondition (and (on ?x ?y) (clear ?x) (arm-empty))
    :effect (and (holding ?x) (clear ?y) (not (on ?x ?y)) (not (clear ?x)) (not (arm-empty)))
  )
)
"""

BLOCKSWORLD_PROBLEM = """\
(define (problem bw-simple)
  (:domain blocksworld)
  (:objects b1 b2 b3 - block)
  (:init
    (clear b1)
    (on b1 b2)
    (on b2 b3)
    (ontable b3)
    (arm-empty)
  )
  (:goal (and (on b3 b2) (on b2 b1) (ontable b1)))
)
"""

# Valid plan: reverse the stack b1/b2/b3 -> b3/b2/b1
BLOCKSWORLD_VALID_PLAN = """\
(unstack b1 b2)
(put-down b1)
(unstack b2 b3)
(put-down b2)
(pick-up b2)
(stack b2 b1)
(pick-up b3)
(stack b3 b2)
"""

# Invalid plan: tries to stack without holding
BLOCKSWORLD_INVALID_PLAN = """\
(unstack b1 b2)
(stack b1 b3)
"""


# ---------------------------------------------------------------------------
# Numeric domain: logistics with fuel
# ---------------------------------------------------------------------------

LOGISTICS_FUEL_DOMAIN = """\
(define (domain logistics-fuel)
  (:requirements :strips :typing :numeric-fluents)
  (:types location truck package)
  (:predicates
    (at-truck ?t - truck ?l - location)
    (at-pkg ?p - package ?l - location)
    (in ?p - package ?t - truck)
    (connected ?l1 - location ?l2 - location)
  )
  (:functions
    (fuel ?t - truck)
    (distance ?l1 - location ?l2 - location)
  )

  (:action drive
    :parameters (?t - truck ?from - location ?to - location)
    :precondition (and
      (at-truck ?t ?from)
      (connected ?from ?to)
      (>= (fuel ?t) (distance ?from ?to))
    )
    :effect (and
      (not (at-truck ?t ?from))
      (at-truck ?t ?to)
      (decrease (fuel ?t) (distance ?from ?to))
    )
  )

  (:action load
    :parameters (?p - package ?t - truck ?l - location)
    :precondition (and (at-truck ?t ?l) (at-pkg ?p ?l))
    :effect (and (not (at-pkg ?p ?l)) (in ?p ?t))
  )

  (:action unload
    :parameters (?p - package ?t - truck ?l - location)
    :precondition (and (at-truck ?t ?l) (in ?p ?t))
    :effect (and (at-pkg ?p ?l) (not (in ?p ?t)))
  )
)
"""

LOGISTICS_FUEL_PROBLEM = """\
(define (problem deliver-pkg)
  (:domain logistics-fuel)
  (:objects
    truck1 - truck
    loc1 loc2 loc3 - location
    pkg1 - package
  )
  (:init
    (at-truck truck1 loc1)
    (at-pkg pkg1 loc2)
    (connected loc1 loc2)
    (connected loc2 loc1)
    (connected loc2 loc3)
    (connected loc3 loc2)
    (= (fuel truck1) 100)
    (= (distance loc1 loc2) 10)
    (= (distance loc2 loc1) 10)
    (= (distance loc2 loc3) 15)
    (= (distance loc3 loc2) 15)
  )
  (:goal (at-pkg pkg1 loc3))
)
"""

# Valid plan: drive to loc2, load, drive to loc3, unload
LOGISTICS_FUEL_VALID_PLAN = """\
(drive truck1 loc1 loc2)
(load pkg1 truck1 loc2)
(drive truck1 loc2 loc3)
(unload pkg1 truck1 loc3)
"""

# Invalid plan: not enough fuel (artificially bad route)
LOGISTICS_FUEL_INVALID_PLAN = """\
(drive truck1 loc1 loc2)
(drive truck1 loc2 loc3)
(drive truck1 loc3 loc2)
(drive truck1 loc2 loc3)
(drive truck1 loc3 loc2)
(drive truck1 loc2 loc3)
(drive truck1 loc3 loc2)
"""


# ---------------------------------------------------------------------------
# Typed hierarchy: vehicles + cargo (for subtype compatibility checks)
# ---------------------------------------------------------------------------

TYPED_HIERARCHY_DOMAIN = """\
(define (domain vhcl)
  (:requirements :strips :typing)
  (:types
    vehicle cargo - object
    truck plane - vehicle)
  (:predicates
    (parked ?v - vehicle)
    (stored ?c - cargo)
  )

  (:action start
    :parameters (?v - vehicle)
    :precondition (parked ?v)
    :effect (not (parked ?v))
  )
)
"""

TYPED_HIERARCHY_PROBLEM = """\
(define (problem vhcl-p1)
  (:domain vhcl)
  (:objects
    truck1 - truck
    plane1 - plane
    box1 - cargo
  )
  (:init
    (parked truck1)
    (parked plane1)
    (stored box1)
  )
  (:goal (and (not (parked truck1)) (not (parked plane1))))
)
"""

# Subtype plan: (start truck1) passes a `truck` where `vehicle` is expected.
# Must be accepted — PDDL typing is hierarchical.
TYPED_HIERARCHY_SUBTYPE_PLAN = """\
(start truck1)
(start plane1)
"""

# Sibling-branch plan: (start box1) passes a `cargo` where `vehicle` is
# expected. Must be rejected — cargo is not in vehicle's subtree.
TYPED_HIERARCHY_SIBLING_PLAN = """\
(start box1)
"""


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def write_pddl_files(tmp_path, domain_str, problem_str=None, plan_str=None):
    """Write PDDL strings to temp files and return their paths."""
    domain_file = tmp_path / "domain.pddl"
    domain_file.write_text(domain_str)
    paths = {"domain": str(domain_file)}

    if problem_str is not None:
        problem_file = tmp_path / "problem.pddl"
        problem_file.write_text(problem_str)
        paths["problem"] = str(problem_file)

    if plan_str is not None:
        plan_file = tmp_path / "plan.txt"
        plan_file.write_text(plan_str)
        paths["plan"] = str(plan_file)

    return paths


@pytest.fixture
def classical_files(tmp_path):
    """Blocksworld domain/problem/plan files."""
    return write_pddl_files(
        tmp_path, BLOCKSWORLD_DOMAIN, BLOCKSWORLD_PROBLEM, BLOCKSWORLD_VALID_PLAN
    )


@pytest.fixture
def classical_invalid_files(tmp_path):
    """Blocksworld with an invalid plan."""
    return write_pddl_files(
        tmp_path, BLOCKSWORLD_DOMAIN, BLOCKSWORLD_PROBLEM, BLOCKSWORLD_INVALID_PLAN
    )


@pytest.fixture
def numeric_files(tmp_path):
    """Logistics-fuel domain/problem/plan files."""
    return write_pddl_files(
        tmp_path, LOGISTICS_FUEL_DOMAIN, LOGISTICS_FUEL_PROBLEM, LOGISTICS_FUEL_VALID_PLAN
    )


@pytest.fixture
def numeric_invalid_files(tmp_path):
    """Logistics-fuel with a plan that runs out of fuel."""
    return write_pddl_files(
        tmp_path, LOGISTICS_FUEL_DOMAIN, LOGISTICS_FUEL_PROBLEM, LOGISTICS_FUEL_INVALID_PLAN
    )
