"""KernelAI MCP server."""

from mcp.server import MCPServer
from mcp_server.tools.web_search import web_search
from mcp_server.tools.sql_executor import sql_executor
from mcp_server.tools.shell import shell
from mcp_server.tools.linear_systems import solve_linear_system, check_linear_system_answer


mcp = MCPServer("KernelAI Tools")

mcp.tool()(solve_linear_system)
mcp.tool()(check_linear_system_answer)
mcp.tool()(web_search)
mcp.tool()(sql_executor)
mcp.tool()(shell)

if __name__ == "__main__":
    mcp.run(
        transport="streamable-http",
        host="0.0.0.0",
        port=8001,
    )