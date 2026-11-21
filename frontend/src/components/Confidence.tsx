const labels = ["Guessing", "Unsure", "Somewhat", "Fairly sure", "Certain"];

/** A 1–5 self-rating, compared later with verified results (calibration). */
export default function Confidence({
  label,
  value,
  onChange,
  disabled,
}: {
  label: string;
  value: number | null;
  onChange: (value: number) => void;
  disabled?: boolean;
}) {
  return (
    <fieldset className="confidence" disabled={disabled}>
      <legend>{label}</legend>
      <div>
        {labels.map((text, index) => (
          <button
            type="button"
            key={text}
            aria-pressed={value === index + 1}
            onClick={() => onChange(index + 1)}
            title={text}
          >
            <strong>{index + 1}</strong>
            <span>{text}</span>
          </button>
        ))}
      </div>
    </fieldset>
  );
}
