"""Exact, guided practice for two linear equations in x and y."""

import os

import httpx
import streamlit as st


API_BASE_URL = os.getenv("API_BASE_URL", "http://127.0.0.1:8000").rstrip("/")
EXAMPLES = {
    "Whole-number solution": (("1", "1", "5"), ("1", "-1", "1")),
    "Fractional solution": (("1", "1", "1"), ("1", "-1", "0")),
    "No solution": (("1", "1", "2"), ("2", "2", "5")),
    "Infinitely many solutions": (("1", "1", "2"), ("2", "2", "4")),
    "Custom system": (("1", "1", "5"), ("1", "-1", "1")),
}


def clear_practice():
    for key in ("ls_result", "ls_system", "ls_feedback"):
        st.session_state[key] = None
    st.session_state.ls_hint = False
    st.session_state.ls_reveal = False
    st.session_state.ls_x = ""
    st.session_state.ls_y = ""


def change_example():
    clear_practice()
    for index, row in enumerate(EXAMPLES[st.session_state.ls_example], start=1):
        for name, value in zip(("a", "b", "c"), row):
            st.session_state[f"ls_{name}{index}"] = value


def call_api(action, body):
    try:
        response = httpx.post(
            f"{API_BASE_URL}/tutoring/linear-systems/{action}",
            json=body,
            timeout=10.0,
        )
        response.raise_for_status()
        payload = response.json()
        if not isinstance(payload, dict) or payload.get("classification") not in {"unique", "infinite", "none"}:
            raise ValueError("Unexpected math response")
        return payload
    except httpx.HTTPStatusError as exc:
        if exc.response.status_code == 422:
            st.error("Check the inputs. Use numbers, decimals, or fractions such as 3/2, with a nonzero denominator.")
        else:
            st.error("The math service could not complete this request. Please try again.")
    except httpx.HTTPError:
        st.error("Could not reach the math service. Start the KernelAI API and try again.")
    except ValueError:
        st.error("The math service returned an unexpected response. Check API_BASE_URL and restart the API.")
    return None


st.set_page_config(page_title="Linear Systems · KernelAI", page_icon="🧮", layout="centered")
st.title("Linear Systems Tutor")
st.caption("Prototype · Two equations, two unknowns · Exact arithmetic")
st.write("Practice elimination, then check your answer in both original equations. No LLM or database credentials are needed.")

if "ls_example" not in st.session_state:
    st.session_state.ls_example = next(iter(EXAMPLES))
    change_example()

st.selectbox("Choose a system", list(EXAMPLES), key="ls_example", on_change=change_example)
with st.form("linear_system"):
    st.caption("Each row has the form a × x + b × y = c. Edit the coefficients, then apply the system.")
    equations = []
    for index in (1, 2):
        st.write(f"**Equation {index}**")
        columns = st.columns(3)
        row = {}
        for column, name in zip(columns, ("a", "b", "c")):
            row[name] = column.text_input(
                f"{name}{index}", key=f"ls_{name}{index}", max_chars=32,
                help="Integer, decimal, or fraction, such as -2 or 3/2.",
            )
        equations.append(row)
    apply_system = st.form_submit_button("Apply system", type="primary")

if apply_system:
    clear_practice()
    result = call_api("solve", {"equations": equations})
    if result is not None:
        st.session_state.ls_system = {"equations": equations}
        st.session_state.ls_result = result

result = st.session_state.ls_result
if result is None:
    st.info("Apply a system to start practicing. Reveal the worked solution whenever you’re ready.")
    st.stop()

st.subheader("Your practice system")
for equation in result["equations"]:
    st.latex(equation["latex"])
st.caption("The equations above are the applied problem. Apply again after editing the coefficients.")

if result["classification"] == "unique":
    with st.form("linear_answer"):
        x_column, y_column = st.columns(2)
        x_answer = x_column.text_input("Your x", key="ls_x", max_chars=32)
        y_answer = y_column.text_input("Your y", key="ls_y", max_chars=32)
        st.caption("Integers, decimals, and fractions are accepted. Equivalent fractions count as equal.")
        check_answer = st.form_submit_button("Check my answer")
    if check_answer:
        st.session_state.ls_feedback = None
        if not x_answer.strip() or not y_answer.strip():
            st.warning("Enter both x and y before checking your answer.")
        else:
            feedback = call_api("check", {
                **st.session_state.ls_system,
                "answer": {"x": x_answer, "y": y_answer},
            })
            if feedback is not None:
                st.session_state.ls_feedback = {
                    **feedback, "answer": {"x": x_answer, "y": y_answer},
                }
else:
    st.info(
        "Infinitely many solutions: the equations leave at least one variable free; no single pair is determined."
        if result["classification"] == "infinite" else
        "No solution: the equations contradict each other, so no pair satisfies both."
    )

feedback = st.session_state.ls_feedback
if feedback is not None:
    st.caption(f"Last checked answer: x = {feedback['answer']['x']}, y = {feedback['answer']['y']}")
    if feedback["correct"]:
        st.success(feedback["feedback"])
    else:
        st.warning(feedback["feedback"])
    for check in feedback["checks"]:
        st.latex(check["equation"])
        st.write(f"Left side: {check['lhs']} · Right side: {check['rhs']} · "
                 + ("Equal ✓" if check["satisfied"] else "Not equal"))

hint_column, solution_column = st.columns(2)
if hint_column.button("Give me a hint"):
    st.session_state.ls_hint = True
if solution_column.button("Show worked solution"):
    st.session_state.ls_reveal = True

if st.session_state.ls_hint:
    st.info(result["hint"])

if st.session_state.ls_reveal:
    st.subheader("Worked solution")
    for step in result["steps"]:
        st.write(f"**{step['title']}**")
        st.write(step["explanation"])
        if step["latex"]:
            st.latex(step["latex"])
    if result["solution"] is not None:
        st.latex(r"x = " + result["solution"]["x"] + r"\qquad y = " + result["solution"]["y"])
