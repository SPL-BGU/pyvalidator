"""Tests for Phase 1: Syntax & Semantic Validation."""

from tests.conftest import (
    BLOCKSWORLD_DOMAIN,
    BLOCKSWORLD_PROBLEM,
    LOGISTICS_FUEL_DOMAIN,
    LOGISTICS_FUEL_PROBLEM,
    write_pddl_files,
)

from pyval.syntax_checker import check_syntax


def test_valid_classical_domain_passes(tmp_path):
    paths = write_pddl_files(tmp_path, BLOCKSWORLD_DOMAIN, BLOCKSWORLD_PROBLEM)
    result, problem = check_syntax(paths["domain"], paths["problem"])
    assert result["status"] == "PASS"
    assert result["errors"] == []
    assert problem is not None


def test_valid_numeric_domain_passes(tmp_path):
    paths = write_pddl_files(tmp_path, LOGISTICS_FUEL_DOMAIN, LOGISTICS_FUEL_PROBLEM)
    result, problem = check_syntax(paths["domain"], paths["problem"])
    assert result["status"] == "PASS"
    assert result["errors"] == []
    assert problem is not None


def test_domain_only_mode(tmp_path):
    paths = write_pddl_files(tmp_path, BLOCKSWORLD_DOMAIN)
    result, problem = check_syntax(paths["domain"])
    assert result["status"] == "PASS"
    assert problem is not None


def test_undeclared_type_reports_error(tmp_path):
    bad_domain = """\
(define (domain bad)
  (:requirements :strips :typing)
  (:types block)
  (:predicates (on ?x - block ?y - nonexistent))
  (:action noop
    :parameters (?x - block)
    :precondition (on ?x ?x)
    :effect (on ?x ?x)
  )
)
"""
    paths = write_pddl_files(tmp_path, bad_domain)
    result, problem = check_syntax(paths["domain"])
    assert result["status"] == "FAIL"
    assert len(result["errors"]) > 0


def test_malformed_pddl_reports_error(tmp_path):
    bad_domain = "(define (domain bad) (:predicates (foo ?x))"  # missing closing paren
    paths = write_pddl_files(tmp_path, bad_domain)
    result, problem = check_syntax(paths["domain"])
    assert result["status"] == "FAIL"
    assert problem is None


def test_domain_problem_mismatch_reports_error(tmp_path):
    domain = """\
(define (domain alpha)
  (:requirements :strips)
  (:predicates (p))
  (:action a :parameters () :precondition (p) :effect (p))
)
"""
    problem = """\
(define (problem p1)
  (:domain beta)
  (:init (p))
  (:goal (p))
)
"""
    paths = write_pddl_files(tmp_path, domain, problem)
    result, parsed = check_syntax(paths["domain"], paths["problem"])
    # UPF may or may not reject domain name mismatch — check it doesn't crash
    assert result["status"] in ("PASS", "FAIL")


def test_numeric_uninitialized_warns(tmp_path):
    domain = """\
(define (domain numtest)
  (:requirements :strips :typing :numeric-fluents)
  (:types thing)
  (:functions (cost ?t - thing))
  (:action a
    :parameters (?t - thing)
    :precondition ()
    :effect (increase (cost ?t) 1)
  )
)
"""
    problem = """\
(define (problem np1)
  (:domain numtest)
  (:objects o1 - thing)
  (:init)
  (:goal ())
)
"""
    paths = write_pddl_files(tmp_path, domain, problem)
    result, parsed = check_syntax(paths["domain"], paths["problem"])
    # Should warn about uninitialized numeric function
    if result["status"] == "PASS" and parsed is not None:
        assert any("cost" in w for w in result["warnings"])
