"""KernelAI MCP server."""

from mcp.server import MCPServer
from mcp_server.tools.math_studio import verify_inequality_answer, verify_statistics_answer
from mcp_server.tools.algebra import algebra_problems, verify_algebra_answer, verify_symbolic_answer
from mcp_server.tools.web_search import web_search
from mcp_server.tools.sql_executor import sql_executor
from mcp_server.tools.shell import shell
from mcp_server.tools.linear_systems import solve_linear_system, check_linear_system_answer
from mcp_server.tools.probability import run_probability_experiment
from mcp_server.tools.geometry import verify_geometry_answer
from mcp_server.tools.learners import get_learner_profile, plan_learner_next_step


mcp = MCPServer("KernelAI Tools")

mcp.tool()(verify_inequality_answer)
mcp.tool()(verify_statistics_answer)
mcp.tool()(solve_linear_system)
mcp.tool()(check_linear_system_answer)
mcp.tool()(run_probability_experiment)
mcp.tool()(verify_geometry_answer)
mcp.tool()(get_learner_profile)
mcp.tool()(plan_learner_next_step)
mcp.tool()(web_search)
mcp.tool()(sql_executor)
mcp.tool()(shell)
mcp.tool()(algebra_problems)
mcp.tool()(verify_algebra_answer)
mcp.tool()(verify_symbolic_answer)

if __name__ == "__main__":
    mcp.run(
        transport="streamable-http",
        host="0.0.0.0",
        port=8001,
    )