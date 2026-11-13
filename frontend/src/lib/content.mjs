// Keep model control fragments out of the normal answer, with raw output available separately.
export function answerText(content) {
  const source = String(content || "");
  const end = source.lastIndexOf("</think>");
  return (
    end >= 0 ? source.slice(end + 8) : source.replace(/<think>[\s\S]*$/g, "")
  ).trim();
}

export function numericPreview(text) {
  return text
    .split(/[\s,;]+/)
    .filter(Boolean)
    .map((value) => {
      const parts = value.split("/");
      return parts.length === 2
        ? Number(parts[0]) / Number(parts[1])
        : Number(value);
    })
    .filter(Number.isFinite)
    .slice(0, 100);
}

export function researchError(message) {
  if (/401|authentication|key is blocked/i.test(message || ""))
    return "The model provider rejected the server credentials. Update the server’s API key, restart the API, and try again.";
  if (/429|quota|rate limit/i.test(message || ""))
    return "The research service is at its limit. Wait a little and try again.";
  return "The research could not be completed. Check the server connection and try again.";
}
