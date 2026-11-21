import type { GeometryProblem } from "../lib/types";

const n = (value: string) => Number(value);

/** A schematic, not-to-scale sketch of the problem; values come from the bank. */
export default function GeometryFigure({
  problem,
}: {
  problem: GeometryProblem;
}) {
  const p = problem.params;
  const stroke = { stroke: "#2c6c4d", strokeWidth: 2, fill: "#eef4ea" };
  const label = (
    x: number,
    y: number,
    text: string,
    anchor: "start" | "middle" | "end" = "middle",
  ) => (
    <text x={x} y={y} textAnchor={anchor} className="figure-label">
      {text}
    </text>
  );
  let body;
  switch (problem.kind) {
    case "rectangle_area":
    case "rectangle_perimeter":
      body = (
        <>
          <rect x="50" y="35" width="140" height="80" rx="2" {...stroke} />
          {label(120, 132, p.width)}
          {label(38, 80, p.height, "end")}
        </>
      );
      break;
    case "triangle_area":
      body = (
        <>
          <polygon points="40,125 200,125 140,30" {...stroke} />
          <line
            x1="140"
            y1="30"
            x2="140"
            y2="125"
            stroke="#7c877f"
            strokeDasharray="4 4"
          />
          {label(120, 143, `base ${p.base}`)}
          {label(146, 85, `h ${p.height}`, "start")}
        </>
      );
      break;
    case "circle_area":
    case "circle_circumference":
      body = (
        <>
          <circle cx="120" cy="80" r="55" {...stroke} />
          <line
            x1="120"
            y1="80"
            x2="175"
            y2="80"
            stroke="#173f35"
            strokeWidth="2"
          />
          <circle cx="120" cy="80" r="3" fill="#173f35" />
          {label(147, 72, `r = ${p.radius}`)}
        </>
      );
      break;
    case "pythagoras_hypotenuse":
    case "pythagoras_leg":
      body = (
        <>
          <polygon points="60,125 190,125 60,35" {...stroke} />
          <polyline
            points="60,113 72,113 72,125"
            fill="none"
            stroke="#173f35"
          />
          {problem.kind === "pythagoras_hypotenuse" ? (
            <>
              {label(125, 143, p.b)}
              {label(48, 84, p.a, "end")}
              {label(135, 72, "?", "start")}
            </>
          ) : (
            <>
              {label(125, 143, "?")}
              {label(48, 84, p.leg, "end")}
              {label(135, 72, p.hypotenuse, "start")}
            </>
          )}
        </>
      );
      break;
    case "triangle_angle":
      body = (
        <>
          <polygon points="35,125 205,125 95,35" {...stroke} />
          {label(62, 118, `${p.angle_a}°`)}
          {label(180, 118, `${p.angle_b}°`)}
          {label(97, 60, "?")}
        </>
      );
      break;
    default: {
      const xs = [n(p.x1), n(p.x2)];
      const ys = [n(p.y1), n(p.y2)];
      const span = Math.max(1, ...xs.map(Math.abs), ...ys.map(Math.abs));
      const sx = (x: number) => 120 + (x / span) * 85;
      const sy = (y: number) => 80 - (y / span) * 58;
      body = (
        <>
          <line x1="20" y1="80" x2="220" y2="80" stroke="#c9d3c6" />
          <line x1="120" y1="10" x2="120" y2="150" stroke="#c9d3c6" />
          <line
            x1={sx(xs[0])}
            y1={sy(ys[0])}
            x2={sx(xs[1])}
            y2={sy(ys[1])}
            stroke="#2c6c4d"
            strokeWidth="2"
            strokeDasharray={problem.kind === "slope" ? undefined : "5 4"}
          />
          {[0, 1].map((i) => (
            <g key={i}>
              <circle cx={sx(xs[i])} cy={sy(ys[i])} r="4" fill="#173f35" />
              {label(
                sx(xs[i]) + 6,
                sy(ys[i]) - 8,
                `(${xs[i]}, ${ys[i]})`,
                "start",
              )}
            </g>
          ))}
        </>
      );
    }
  }
  return (
    <svg
      className="geometry-figure"
      viewBox="0 0 240 155"
      role="img"
      aria-label={`Sketch, not to scale: ${problem.prompt}`}
    >
      {body}
    </svg>
  );
}
