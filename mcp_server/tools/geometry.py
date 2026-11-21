"""Expose exact geometry checks to skill workers (same function as the studio API)."""

from tutoring.geometry import PARAMS, GeometrySpec, verify


async def verify_geometry_answer(kind: str, params: dict[str, str], answer: str) -> dict:
    """Check a geometry answer exactly with SymPy.

    kind and its params (numeric strings):
    rectangle_area / rectangle_perimeter: width, height; triangle_area: base, height;
    circle_area / circle_circumference: radius; pythagoras_hypotenuse: a, b;
    pythagoras_leg: hypotenuse, leg; triangle_angle: angle_a, angle_b (degrees);
    distance / midpoint / slope: x1, y1, x2, y2.
    Answers may be exact (9*pi, 3*sqrt(2), 7/2), correctly rounded decimals,
    "(x, y)" for a midpoint, or "undefined" for a vertical slope.
    """
    try:
        return verify(GeometrySpec(kind=kind, params=params), answer)
    except ValueError as exc:
        return {"status": "unsupported", "message": str(exc), "supported_kinds": sorted(PARAMS)}
