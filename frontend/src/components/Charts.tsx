import type { Segment } from "../lib/types";

export function NumberLine({ segments }: { segments?: Segment[] }) {
  const endpoints =
    segments
      ?.flatMap((s) => [s.low, s.high])
      .filter((v): v is number => v !== null) || [];
  const scale = Math.max(6, ...endpoints.map((v) => Math.abs(v) + 2));
  const position = (v: number) => 35 + ((v + scale) / (2 * scale)) * 510;
  const ticks = Array.from({ length: 7 }, (_, i) => ((i - 3) * scale) / 3);
  return (
    <svg
      viewBox="0 0 580 115"
      role="img"
      aria-label={
        segments
          ? "Verified solution intervals on a number line"
          : "Number line preview; submit a correct answer to reveal the solution"
      }
    >
      <line x1="24" x2="556" y1="48" y2="48" stroke="#b8c6bf" strokeWidth="2" />
      <path
        d="M30 43L24 48L30 53M550 43L556 48L550 53"
        fill="none"
        stroke="#b8c6bf"
        strokeWidth="2"
      />
      {ticks.map((t) => (
        <g key={t}>
          <line
            x1={position(t)}
            x2={position(t)}
            y1="42"
            y2="54"
            stroke="#b8c6bf"
          />
          <text
            x={position(t)}
            y="79"
            textAnchor="middle"
            fill="#79867e"
            fontSize="12"
          >
            {Number(t.toFixed(1))}
          </text>
        </g>
      ))}
      {segments?.map((s, i) => (
        <g key={i}>
          <line
            x1={s.low === null ? 25 : position(s.low)}
            x2={s.high === null ? 555 : position(s.high)}
            y1="48"
            y2="48"
            stroke="#3c8c68"
            strokeWidth="5"
          />
          {s.low !== null && (
            <circle
              cx={position(s.low)}
              cy="48"
              r="6"
              fill={s.left_open ? "#fff" : "#3c8c68"}
              stroke="#3c8c68"
              strokeWidth="3"
            />
          )}
          {s.high !== null && (
            <circle
              cx={position(s.high)}
              cy="48"
              r="6"
              fill={s.right_open ? "#fff" : "#3c8c68"}
              stroke="#3c8c68"
              strokeWidth="3"
            />
          )}
        </g>
      ))}
    </svg>
  );
}

export function DataPlot({ values }: { values: number[] }) {
  const max = Math.max(1, ...values.map(Math.abs));
  return (
    <svg
      viewBox="0 0 580 150"
      role="img"
      aria-label={`Bar chart of ${values.length} entered observations`}
    >
      <line x1="30" x2="550" y1="72" y2="72" stroke="#cbd7d1" />
      {values.slice(0, 24).map((value, i, all) => {
        const width = 500 / all.length;
        const h = (Math.abs(value) / max) * 52;
        return (
          <g key={i}>
            <rect
              x={40 + i * width}
              y={value >= 0 ? 72 - h : 72}
              width={Math.max(2, width - 10)}
              height={Math.max(1, h)}
              rx="4"
              fill={i % 2 ? "#b7cebc" : "#5e9473"}
            />
            <text
              x={40 + i * width + (width - 10) / 2}
              y="145"
              textAnchor="middle"
              fill="#6d7c72"
              fontSize="12"
            >
              {Number(value.toFixed(2))}
            </text>
          </g>
        );
      })}
    </svg>
  );
}
