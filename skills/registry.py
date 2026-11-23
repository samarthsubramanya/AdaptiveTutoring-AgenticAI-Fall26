"""Local skill registry for KernelAI."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


SKILLS_DIR = Path(__file__).parent


@dataclass(frozen=True)
class Skill:
    """
    Definition of a skill available to KernelAI.
    """

    name: str
    description: str
    path: Path
    allowed_tools: set[str]

    def load(self) -> str:
        """
        Load and return the full skill instructions.
        """
        return self.path.read_text(
            encoding="utf-8"
        )


SKILLS: dict[str, Skill] = {
    "equation_solving": Skill(name="equation_solving", description="Mathematics: solve confirmed polynomial equations using deterministic verification.",
        path=SKILLS_DIR.parent / "vault/skills/math/equation-solving/equation-solving.md", allowed_tools={"verify_symbolic_answer"}),
    "factoring": Skill(name="factoring", description="Mathematics: check factored form using deterministic verification.",
        path=SKILLS_DIR.parent / "vault/skills/math/factoring/factoring.md", allowed_tools={"verify_symbolic_answer"}),
    "expression_expansion": Skill(name="expression_expansion", description="Mathematics: check an expanded expression using deterministic verification.",
        path=SKILLS_DIR.parent / "vault/skills/math/expression-expansion/expression-expansion.md", allowed_tools={"verify_symbolic_answer"}),
    "polynomial_derivatives": Skill(name="polynomial_derivatives", description="Mathematics: check a polynomial derivative using deterministic verification.",
        path=SKILLS_DIR.parent / "vault/skills/math/polynomial-derivatives/polynomial-derivatives.md", allowed_tools={"verify_symbolic_answer"}),
    "solution_checking": Skill(name="solution_checking", description="Mathematics: verify a student solution using deterministic verification.",
        path=SKILLS_DIR.parent / "vault/skills/math/solution-checking/solution-checking.md", allowed_tools={"verify_symbolic_answer", "verify_algebra_answer"}),
    "interactive_tutor": Skill(name="interactive_tutor", description="Run server-controlled interactive tutoring: attempts, graduated hints, prerequisite review, fresh unaided checks and persistent learner evidence.",
        path=SKILLS_DIR.parent / "vault/skills/math/interactive-tutor/interactive-tutor.md",
        allowed_tools={"start_learning_journey", "get_learning_journey", "submit_learning_attempt", "request_learning_hint", "advance_learning_journey"}),
    "algebra": Skill(
        name="algebra",
        description=(
            "Check student answers to eight predefined introductory algebra "
            "equations, or verify custom polynomial algebra and derivatives with SymPy."
        ),
        path=SKILLS_DIR.parent / "vault/skills/math/algebra/algebra.md",
        allowed_tools={"algebra_problems", "verify_algebra_answer", "verify_symbolic_answer"},
    ),
    "inequalities": Skill(
        name="inequalities",
        description="Verify full real solution sets for linear and quadratic inequalities, including endpoints.",
        path=SKILLS_DIR.parent / "vault/skills/math/inequalities/inequalities.md",
        allowed_tools={"verify_inequality_answer"},
    ),
    "statistics": Skill(
        name="statistics",
        description="Check descriptive statistics on explicit data, with population/sample conventions.",
        path=SKILLS_DIR.parent / "vault/skills/math/statistics/statistics.md",
        allowed_tools={"verify_statistics_answer"},
    ),
    "text2sql": Skill(
        name="text2sql",
        description=(
            "Answer questions using the connected PostgreSQL "
            "database through schema discovery and read-only SQL."
        ),
        path=SKILLS_DIR.parent / "vault/skills/data/text2sql/text2sql.md",
        allowed_tools={
            "sql_executor",
        },
    ),

    "web_search": Skill(
        name="web_search",
        description=(
            "Research current or external information using "
            "web search."
        ),
        path=SKILLS_DIR.parent / "vault/skills/research/web-search/web-search.md",
        allowed_tools={
            "web_search",
        },
    ),
    "linear_systems": Skill(
        name="linear_systems",
        description=(
            "Solve two linear equations in x and y with exact worked steps, "
            "or check a student's answer by substitution into both equations."
        ),
        path=SKILLS_DIR.parent / "vault/skills/math/linear-systems/linear-systems.md",
        allowed_tools={"solve_linear_system", "check_linear_system_answer"},
    ),
    "probability": Skill(
        name="probability",
        description=(
            "Explore coin and dice probability through reproducible simulations, "
            "theoretical distributions, and sampling-variation comparisons."
        ),
        path=SKILLS_DIR.parent / "vault/skills/math/probability/probability.md",
        allowed_tools={"run_probability_experiment"},
    ),
    "geometry": Skill(
        name="geometry",
        description=(
            "Check area, perimeter, Pythagoras, triangle-angle, distance, midpoint "
            "and slope answers exactly with SymPy."
        ),
        path=SKILLS_DIR.parent / "vault/skills/math/geometry/geometry.md",
        allowed_tools={"verify_geometry_answer"},
    ),
    "retrieve_first_gate": Skill(
        name="retrieve_first_gate",
        description="Teaching: Before any help, have a returning learner recall from memory; hints open only after an unaided attempt. Pair with a math skill.",
        path=SKILLS_DIR.parent / "vault/skills/teaching/retrieve-first-gate/retrieve-first-gate.md",
        allowed_tools={"get_learner_profile", "plan_learner_next_step"},
    ),
    "progressive_hint_ladder": Skill(
        name="progressive_hint_ladder",
        description="Teaching: Give graduated hints (conceptual, strategic, procedural) with a short learner reflection before each escalation. Pair with a math skill.",
        path=SKILLS_DIR.parent / "vault/skills/teaching/progressive-hint-ladder/progressive-hint-ladder.md",
        allowed_tools={"get_learner_profile", "plan_learner_next_step"},
    ),
    "unassisted_evidence_checkpoint": Skill(
        name="unassisted_evidence_checkpoint",
        description="Teaching: After an assisted success, set a fresh hint-free problem to establish what the learner can do alone. Pair with a math skill.",
        path=SKILLS_DIR.parent / "vault/skills/teaching/unassisted-evidence-checkpoint/unassisted-evidence-checkpoint.md",
        allowed_tools={"get_learner_profile", "plan_learner_next_step"},
    ),
    "fading_manager": Skill(
        name="fading_manager",
        description="Teaching: Reduce support as verified unaided successes accumulate across sessions, restore it after misses, and name each change. Pair with a math skill.",
        path=SKILLS_DIR.parent / "vault/skills/teaching/fading-manager/fading-manager.md",
        allowed_tools={"get_learner_profile", "plan_learner_next_step"},
    ),
    "confidence_calibration_check": Skill(
        name="confidence_calibration_check",
        description="Teaching: Capture confidence before and after feedback and compare it with verified accuracy. Pair with a math skill.",
        path=SKILLS_DIR.parent / "vault/skills/teaching/confidence-calibration-check/confidence-calibration-check.md",
        allowed_tools={"get_learner_profile", "plan_learner_next_step"},
    ),
}


def get_skill(
    name: str,
) -> Skill:
    """
    Return a skill definition by name.
    """

    try:
        return SKILLS[name]

    except KeyError as exc:
        raise ValueError(
            f"Unknown skill {name!r}."
        ) from exc


def list_skills() -> list[dict[str, object]]:
    """
    Return lightweight descriptions of all delegatable skills.

    Full skill prompts are intentionally excluded so the
    orchestrator does not need to load every skill into context.
    """

    return [
        {
            "name": skill.name,
            "description": skill.description,
            "allowed_tools": sorted(
                skill.allowed_tools
            ),
        }
        for skill in SKILLS.values()
    ]