# Learning studio validation — November 13, 2026

## Automated checks

- 137 Python tests passed: `tests/test_studio.py`, `tests/test_algebra.py`,
  `tests/test_algebra_api.py`, `tests/test_custom_math.py`,
  `tests/test_observability.py`, and `tests/test_tool_observability.py`.
- Three frontend tests passed: provider-control-fragment filtering, numeric chart
  previews without evaluation, and friendly provider-error messages.
- TypeScript and Vite production build passed; Prettier check passed.
- `bash -n start-studio.sh` passed. A smoke launch on API 18030, MCP 18031, and frontend 5174 started all three services; Ctrl+C stopped them.
- Both new MCP tools were discovered and executed over a live local MCP server:
  a quadratic interval union and sample variance both returned `correct`.

## Browser checks

At desktop (1440 × 1000) and mobile (390 × 844) widths, checked navigation,
layout, labels, and actual backend feedback. No fabricated data was injected.

- `2*x + 3 <= 11`: `(-inf, 4)` returns incorrect; `(-inf, 4]` returns correct.
- The number line renders a closed endpoint at 4 after verification. A browser
  check exposed SymPy boolean serialization; the fix and HTTP regression assert
  ordinary JSON booleans for every endpoint.
- Statistics `[4, 7, 7, 9, 13]`: mean 8 and sample variance 11 both pass.
- Guided algebra: `3(x - 2) = 12`, answer 6, then next-problem transition pass.
- Journal records real checks, persists across reload, and clear/undo restores it.
- Mobile drawer opens, closes with Escape, and supports navigation. Closed mobile
  links are inert; keyboard focus stays within the open drawer.
- Research submission reached the existing server. The provider rejected the
  configured key with 401 (`Key is blocked`). The frontend displayed an actionable
  credential message and allowed another request. A successful end-to-end model
  synthesis could not be verified with this key. No completion is claimed.

Screenshots were saved outside the source checkout in the shared project's
`pdocs/learning-studio-screenshots/` folder. They show real UI/API interactions.
Practice counts are browser-local records, not learning gains or mastery scores.

## Request-handling rationale

Serialized polling avoids overlapping status fetches; AbortController cleanup
and response guards stop stale data replacing a newer view. Research checking
pauses after 15 minutes and can resume without resubmitting the server job.

References inspected during implementation:

- [React: synchronizing with effects](https://react.dev/learn/synchronizing-with-effects)
- [Handling API request race conditions in React](https://dev.to/sebastienlorber/handling-api-request-race-conditions-in-react-4j5b)
- [Async APIs: The 202 Accepted + Polling Pattern for Long-Running Operations](https://dev.to/apikumo/async-apis-the-202-accepted-polling-pattern-for-long-running-operations-5e37)

The existing API's request/status contract was retained. The frontend does not
interpret successful submission as completed research.
