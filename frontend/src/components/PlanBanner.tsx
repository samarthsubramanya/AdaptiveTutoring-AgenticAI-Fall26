import Icon from "./Icon";
import type { Plan } from "../lib/types";

const titles: Record<Plan["action"], string> = {
  start: "Getting started",
  practice: "Keep practising",
  retrieve: "Recall first",
  unassisted_check: "Unaided check",
  prerequisite_review: "Review a prerequisite",
};
const supportText = {
  full: "Full support · up to 3 hints",
  light: "Light support · 1 hint",
  none: "Independent · no hints",
};

/** The tutor's next step for this subject, justified by the learner's verified record. */
export default function PlanBanner({
  plan,
  active,
  onUse,
}: {
  plan: Plan | null;
  active: boolean;
  onUse: () => void;
}) {
  if (!plan) return null;
  const actionable =
    plan.action !== "start" && (plan.suggested?.length ?? 0) > 0;
  return (
    <section
      className={`plan-banner plan-${plan.action}`}
      aria-live="polite"
      aria-label="Your next step"
    >
      <div className="plan-head">
        <span className="eyebrow">YOUR NEXT STEP</span>
        <span className="support-chip">
          {plan.action === "unassisted_check"
            ? supportText.none
            : supportText[plan.support]}
        </span>
      </div>
      <h3>
        {titles[plan.action]}
        {plan.topic_label && plan.action !== "start" && (
          <span> · {plan.topic_label}</span>
        )}
      </h3>
      <p>{plan.reason}</p>
      {actionable && (
        <button className="text-button" onClick={onUse} disabled={active}>
          {active ? (
            <>
              <Icon name="Check" size={15} /> Suggested problem loaded
            </>
          ) : (
            <>
              Try the suggested problem <Icon name="ArrowRight" size={15} />
            </>
          )}
        </button>
      )}
    </section>
  );
}
