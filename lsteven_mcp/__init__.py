"""lsteven_mcp — MCP server implementing the LSteven RSI/EMA9/WMA45 trading method.

Core reading engine is decoupled from the MCP transport (see indicators.py,
form_trap.py, multiframe.py) so it can be reused directly from a web app or
a bot later without going through the MCP protocol at all.
"""

__version__ = "0.1.0"
