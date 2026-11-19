"""Exact solutions and substitution checks for two-variable linear systems."""

import pytest

from tutoring.linear_systems import check_linear_system_answer, solve_linear_system


def equations(a="1", b="1", c="3", d="1", e="-1", f="1"):
    return [{"a": a, "b": b, "c": c}, {"a": d, "b": e, "c": f}]


@pytest.mark.parametrize("rows,solution", [
    (equations(), {"x": "2", "y": "1"}),
    (equations("1/2", "1/3", "1", "1", "-1", "0"), {"x": "6/5", "y": "6/5"}),
    (equations("0.5", "1", "1", "1", "-1", "1"), {"x": "4/3", "y": "1/3"}),
    (equations("0", "2", "3", "4", "0", "-5"), {"x": "-5/4", "y": "3/2"}),
    (equations("2", "0", "3", "0", "-4", "5"), {"x": "3/2", "y": "-5/4"}),
    (equations("1", "2", "0", "3", "4", "0"), {"x": "0", "y": "0"}),
])
def test_unique_solutions_are_exact_and_satisfy_both_originals(rows, solution):
    result = solve_linear_system(rows)
    assert result["classification"] == "unique"
    assert result["solution"] == solution
    assert [step["title"] for step in result["steps"]] == [
        "Eliminate y", "Solve for x", "Substitute to find y", "Verify both original equations",
    ]
    assert all(step["explanation"] and step["latex"] for step in result["steps"])
    assert check_linear_system_answer(rows, solution)["correct"]
    assert check_linear_system_answer(list(reversed(rows)), solution)["correct"]


@pytest.mark.parametrize("rows,classification", [
    (equations("1", "2", "3", "2", "4", "6"), "infinite"),
    (equations("1", "2", "3", "2", "4", "7"), "none"),
    (equations("0", "1", "2", "0", "2", "4"), "infinite"),
    (equations("0", "1", "2", "0", "2", "5"), "none"),
    (equations("0", "0", "0", "2", "3", "4"), "infinite"),
    (equations("0", "0", "1", "2", "3", "4"), "none"),
    (equations("0", "0", "0", "0", "0", "0"), "infinite"),
    (equations("0", "0", "0", "0", "0", "-1"), "none"),
    (equations("1/2", "1/3", "1", "3", "2", "6"), "infinite"),
    (equations("1/2", "1/3", "1", "3", "2", "7"), "none"),
])
def test_dependent_and_zero_rows_are_classified_without_a_fake_solution(rows, classification):
    for ordered in (rows, list(reversed(rows))):
        result = solve_linear_system(ordered)
        assert result["classification"] == classification
        assert result["solution"] is None
        assert result["steps"] and result["hint"]
        assert "parallel" not in str(result).lower()


def test_answer_must_satisfy_both_original_equations_and_never_returns_the_solution():
    result = check_linear_system_answer(equations(), {"x": "1", "y": "2"})
    assert result["correct"] is False
    assert [check["satisfied"] for check in result["checks"]] == [True, False]
    assert result["checks"][1]["lhs"] == "-1"
    assert result["checks"][1]["rhs"] == "1"
    assert "solution" not in result


def test_infinite_system_accepts_a_pair_without_claiming_a_unique_solution():
    rows = equations("1", "1", "3", "2", "2", "6")
    result = check_linear_system_answer(rows, {"x": "-1/2", "y": "3.5"})
    assert result["correct"] is True
    assert result["classification"] == "infinite"
    assert "one of infinitely many" in result["feedback"]
    assert not check_linear_system_answer(rows, {"x": "0", "y": "0"})["correct"]
    assert check_linear_system_answer(equations("0", "0", "0", "0", "0", "0"),
                                      {"x": "13/4", "y": "-12"})["correct"]


def test_inconsistent_system_rejects_every_pair_even_when_one_equation_matches():
    result = check_linear_system_answer(equations("1", "1", "3", "2", "2", "7"),
                                        {"x": "1", "y": "2"})
    assert result["correct"] is False
    assert result["classification"] == "none"
    assert [check["satisfied"] for check in result["checks"]] == [True, False]
    assert "inconsistent" in result["feedback"]


def test_numeric_inputs_are_canonical_and_inputs_stay_unchanged():
    rows = equations(" +0.50 ", "1/2", "1", "1", "-1", "0")
    result = solve_linear_system(rows)
    assert result["equations"][0] == {"a": "1/2", "b": "1/2", "c": "1", "latex": r"\frac{1}{2}x +\frac{1}{2}y = 1"}
    assert rows[0]["a"] == " +0.50 "
    assert result["solution"] == {"x": "1", "y": "1"}


@pytest.mark.parametrize("bad", [
    "", " ", "NaN", "inf", "-Infinity", "1e3", "1_000", "1/0", "0/0",
    "1/2/3", "2+3", "x", "sqrt(2)", "__import__('os').system('id')",
    "9" * 33, "１２", True, 1, 0.5, None, [], {},
])
def test_untrusted_numeric_input_is_rejected_for_equations_and_answers(bad):
    with pytest.raises(ValueError):
        solve_linear_system(equations(a=bad))
    with pytest.raises(ValueError):
        check_linear_system_answer(equations(), {"x": bad, "y": "1"})


@pytest.mark.parametrize("bad", [
    None, {}, [], [{}], [{}, {}, {}],
    [{"a": "1", "b": "2"}, {"a": "1", "b": "2", "c": "3"}],
    [{"a": "1", "b": "2", "c": "3", "d": "4"}, {"a": "1", "b": "2", "c": "3"}],
    [None, {"a": "1", "b": "2", "c": "3"}],
])
def test_invalid_equation_shape_is_rejected(bad):
    with pytest.raises(ValueError):
        solve_linear_system(bad)
    with pytest.raises(ValueError):
        check_linear_system_answer(bad, {"x": "1", "y": "2"})


@pytest.mark.parametrize("bad", [None, [], {}, {"x": "2"}, {"x": "2", "y": "1", "correct": True}])
def test_both_answer_coordinates_and_no_extra_fields_are_required(bad):
    with pytest.raises(ValueError):
        check_linear_system_answer(equations(), bad)
