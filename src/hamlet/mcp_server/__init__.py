# MCP Server module - handles MCP protocol and event reception
"""
MCP Server module for receiving hook events from Claude Code.

This module implements the Model Context Protocol (MCP) server that receives
events from Claude Code hooks (PreToolUse, PostToolUse, Notification, Stop)
and queues them for processing.
"""

from .handlers import register_handlers
from .server import MCPServer

__all__ = ["MCPServer", "register_handlers"]