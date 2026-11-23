"""Vault discoverability and runtime prompts must describe the same math skills."""

from pathlib import Path
import re
from skills.registry import SKILLS


def test_math_skill_sources_and_wikilinks_resolve():
    root = Path(__file__).resolve().parents[1]
    vault = root / "vault"
    names = ["algebra", "inequalities", "statistics", "geometry", "linear_systems", "probability",
             "equation_solving", "factoring", "expression_expansion", "polynomial_derivatives", "solution_checking", "interactive_tutor"]
    for name in names:
        assert SKILLS[name].path.is_relative_to(vault / "skills/math")
        assert SKILLS[name].load().strip()
    for note in (vault / "skills/math").rglob("*.md"):
        for link in re.findall(r"\[\[([^]|]+)(?:\|[^]]+)?\]\]", note.read_text()):
            assert (vault / (link + ".md")).exists(), (note, link)
    assert "[[skills/math/DOMAIN|mathematics]]" in (vault / "skills/REGISTRY.md").read_text()
