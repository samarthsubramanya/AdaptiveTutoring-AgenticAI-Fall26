import Icon from "./Icon";
import type { Verification } from "../lib/types";
export default function Feedback({ result }: { result: Verification | null }) {
  if (!result) return null;
  const correct = result.status === "correct";
  return (
    <div className={`feedback ${correct ? "success" : "retry"}`} role="status">
      <Icon name={correct ? "ShieldCheck" : "CircleHelp"} size={24} />
      <div>
        <strong>
          {correct
            ? "You’ve got it."
            : result.status === "incorrect"
              ? "Almost. Let’s take another look."
              : "This answer hasn’t been graded."}
        </strong>
        <p>{result.message}</p>
      </div>
    </div>
  );
}
