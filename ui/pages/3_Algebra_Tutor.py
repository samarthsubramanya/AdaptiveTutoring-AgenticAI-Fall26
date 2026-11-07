"""Guided algebra practice and LLM-assisted, symbolically checked custom problems."""

import os

import httpx
import streamlit as st


API_BASE_URL = os.getenv("API_BASE_URL", "http://127.0.0.1:8000").rstrip("/")
st.set_page_config(page_title="Algebra Tutor", page_icon="🧮", layout="centered")
st.title("Algebra Tutor")
st.caption("Guided practice · LLM-assisted problems · SymPy verification")
st.info("Practice with hints and retries. Sessions stay in this server's memory for up to one idle hour and reset when the API restarts.")


def api(method: str, path: str, body: dict | None = None):
    try:
        response = httpx.request(method, f"{API_BASE_URL}/tutoring{path}", json=body, timeout=65)
        response.raise_for_status()
        if response.status_code == 204:
            return None
        payload = response.json()
        if path == "/problems":
            if not isinstance(payload, list) or not payload or not all(isinstance(p, dict) and isinstance(p.get("id"), str) and isinstance(p.get("equation"), str) for p in payload) or not any(p["id"] == "distribution-01" for p in payload):
                raise ValueError("Unexpected problem list")
        elif not isinstance(payload, dict):
            raise ValueError("Unexpected tutor response")
        return payload
    except httpx.HTTPStatusError as exc:
        try:
            payload = exc.response.json()
            detail = payload.get("detail", "Request failed.") if isinstance(payload, dict) else "Request failed."
        except ValueError:
            detail = "Request failed."
        if path.startswith("/math/cases"):
            st.error(str(detail))
        else:
            st.error(f"{detail} Refresh the session or start a new one.")
    except httpx.HTTPError:
        st.error("Could not reach the tutor API. Start the services and check API_BASE_URL.")
    except ValueError:
        st.error("The configured server did not return valid tutor API data. Check API_BASE_URL and restart the KernelAI API; another application may be using its port.")
    return None


mode = st.radio("Practice mode", ["Guided practice", "LLM-assisted problems"], horizontal=True)
if mode == "LLM-assisted problems":
    st.write("Ask your own algebra question. Review the model's interpretation, then check your answer or its proposed answer with SymPy.")
    example = st.selectbox("Example problem", [
        "Solve x^2 - 5*x + 6 = 0 over the real numbers.",
        "Factor x^2 - 9.",
        "Expand (x + 2)*(x - 3).",
        "Simplify 3*x + 2*x - 4.",
        "Differentiate x^3 - 2*x with respect to x.",
        "A number doubled and increased by 3 equals 17. Find the number.",
    ])
    with st.form("custom-question"):
        question = st.text_area("Your math question", value=example, max_chars=2000, key=f"question-{example}")
        prepare = st.form_submit_button("Ask math tutor")
    if prepare:
        if not question.strip():
            st.warning("Enter a question first.")
        else:
            with st.spinner("Interpreting the problem and preparing an explanation…"):
                prepared = api("POST", "/math/cases", {"prompt": question})
            if prepared:
                old = st.session_state.get("algebra_case_id")
                if old:
                    api("DELETE", f"/math/cases/{old}")
                st.session_state.algebra_case_id = prepared["case_id"]
                st.rerun()
    case_id = st.session_state.get("algebra_case_id")
    if not case_id:
        st.caption("Supports linear/quadratic equations, polynomial simplification, expansion, factoring, and derivatives. Configure the ASU_LLM settings for this mode.")
        st.stop()
    case = api("GET", f"/math/cases/{case_id}")
    if case is None:
        st.stop()
    st.subheader("Review the interpretation")
    st.write(case["question"])
    st.write(case["problem"]["interpretation"])
    st.caption(f"Operation: {case['problem']['operation']} · Variable: {case['problem']['variable']} · Real-number domain")
    st.latex(case["problem"]["latex"])
    confirmed = st.checkbox("This interpretation matches my question", key=f"confirm-{case_id}")
    st.write("**Model's proposed answer (unverified until checked):**")
    st.code(case["proposed_answer"], language=None)
    with st.expander("LLM explanation — steps are not individually verified"):
        st.write(case["explanation"])
    own_answer = st.text_input("Your answer (optional)", placeholder="For equations, list all real roots, e.g. 2, 3", max_chars=300, key=f"custom-answer-{case_id}")
    own, proposed, hint = st.columns(3)
    if own.button("Check my answer", disabled=not confirmed or not own_answer.strip()):
        if api("POST", f"/math/cases/{case_id}/answers", {"answer": own_answer, "confirmed": True}):
            st.rerun()
    if proposed.button("Verify model answer", disabled=not confirmed):
        if api("POST", f"/math/cases/{case_id}/answers", {"answer": case["proposed_answer"], "confirmed": True}):
            st.rerun()
    if hint.button("Ask for a hint", disabled=not confirmed or len(case["hints"]) >= 3):
        with st.spinner("Preparing a hint…"):
            hinted = api("POST", f"/math/cases/{case_id}/hint", {"confirmed": True})
        if hinted:
            st.rerun()
    if case["verification"]:
        result = case["verification"]
        st.write(f"Checked answer: {case['answer']}")
        if result["status"] == "correct":
            st.success(result["message"])
        elif result["status"] == "incorrect":
            st.warning(result["message"])
        else:
            st.info(result["message"] + " No completed grade was assigned.")
        with st.expander("Symbolic verification evidence"):
            st.json(result)
    for index, text in enumerate(case["hints"], start=1):
        st.write(f"**LLM hint {index}:** {text}")
    st.caption(case["notice"])
    st.caption("Use explicit multiplication in answers (2*x). Solving supports complete real solution sets for linear/quadratic equations; other operations support polynomials up to degree 8. Variable denominators, systems, inequalities, geometry, and proofs are not supported.")
    st.stop()


problems = api("GET", "/problems")
if problems is None:
    st.stop()
options = {problem["id"]: problem for problem in problems}
selected = st.selectbox("Starting problem", list(options),
                        index=list(options).index("distribution-01"),
                        format_func=lambda key: f"{key}: {options[key]['equation']}")

start, close = st.columns(2)
if start.button("Start new session", type="primary"):
    old_id = st.session_state.get("algebra_session_id")
    if old_id:
        # Release the previous slot before creating another one.
        try:
            httpx.delete(f"{API_BASE_URL}/tutoring/sessions/{old_id}", timeout=10)
        except httpx.HTTPError:
            pass
    state = api("POST", "/sessions", {"problem_id": selected})
    st.session_state.algebra_session_id = state["session_id"] if state else None
    st.rerun()

session_id = st.session_state.get("algebra_session_id")
if close.button("End session", disabled=not session_id):
    api("DELETE", f"/sessions/{session_id}")
    st.session_state.algebra_session_id = None
    st.rerun()

if not session_id:
    st.write("Choose a problem and start a session. Submit your own answer before asking for help.")
    st.stop()

state = api("GET", f"/sessions/{session_id}")
if state is None:
    st.stop()
problem = state["problem"]
st.subheader(f"Solve for x · {problem['id']}")
st.latex(problem["latex"])
st.caption(f"Topic: {problem['topic']} · Attempts: {state['attempts']} · Hint level: {state['hint_level']} · Problems solved: {len(state['completed_problem_ids'])}/8")
st.write(state["feedback"])

verification = state["verification"]
if verification:
    label = f"SymPy verification: {verification['status'].replace('_', ' ')}"
    if verification["status"] == "correct":
        st.success(label)
    elif verification["status"] == "incorrect":
        st.warning(label)
    else:
        st.info(label + " — no grade assigned")
    with st.expander("Verification evidence"):
        st.json(verification)

if not state["solved"] and not state["finished"]:
    with st.form(f"answer-{session_id}-{state['round']}", clear_on_submit=True):
        answer = st.text_input("Your answer", placeholder="6, x=6, 1.5, or 3/2", max_chars=80)
        submitted = st.form_submit_button("Check answer")
    if submitted:
        if answer.strip():
            result = api("POST", f"/sessions/{session_id}/answers", {
                "problem_id": problem["id"], "answer": answer, "revision": state["revision"],
            })
            if result is not None:
                st.rerun()
        else:
            st.warning("Enter an answer before checking it.")

hint, advance, refresh = st.columns(3)
if hint.button("Give me a hint", disabled=not state["can_hint"]):
    if api("POST", f"/sessions/{session_id}/hint", {"revision": state["revision"]}) is not None:
        st.rerun()
next_label = "Next problem" if state["solved"] else "Practice prerequisite"
if advance.button(next_label, disabled=not state["can_advance"]):
    if api("POST", f"/sessions/{session_id}/next", {"revision": state["revision"]}) is not None:
        st.rerun()
if refresh.button("Refresh session"):
    st.rerun()

with st.expander("Session history"):
    for event in state["history"]:
        st.json(event)

st.caption("This demo checks final numeric answers, not the validity of every reasoning step. A wrong answer alone does not diagnose a misconception. General chat is separate from this session.")
