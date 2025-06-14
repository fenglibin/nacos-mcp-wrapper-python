import logging
from typing import Any

import uvicorn
from mcp import stdio_server
from mcp.server import FastMCP
from mcp.server.fastmcp.server import lifespan_wrapper
from mcp.server.lowlevel.server import lifespan as default_lifespan

from nacos_mcp_wrapper.server.nacos_server import NacosServer
from nacos_mcp_wrapper.server.nacos_settings import NacosSettings

logger = logging.getLogger(__name__)

class NacosMCP(FastMCP):

	def __init__(self,
			name: str | None = None,
			nacos_settings: NacosSettings | None = None,
			instructions: str | None = None,
			**settings: Any):
		super().__init__(name, instructions, **settings)

		self._mcp_server = NacosServer(
				nacos_settings=nacos_settings,
				name=name or "FastMCP",
				instructions=instructions,
				lifespan=lifespan_wrapper(self, self.settings.lifespan)
				if self.settings.lifespan
				else default_lifespan,
		)
		self.dependencies = self.settings.dependencies

		# Set up MCP protocol handlers
		self._setup_handlers()

	async def run_stdio_async(self) -> None:
		"""Run the server using stdio transport."""
		async with stdio_server() as (read_stream, write_stream):
			await self._mcp_server.register_to_nacos("stdio")
			await self._mcp_server.run(
					read_stream,
					write_stream,
					self._mcp_server.create_initialization_options(),
			)

	async def run_sse_async(self, mount_path: str | None = None) -> None:
		"""Run the server using SSE transport.
		
		Args:
			mount_path: The mount path (e.g. "/github" or "/") for the SSE server, the server will be mounted at the root path.
		"""
		if mount_path is not None:
			starlette_app = self.sse_app(mount_path)
		else:
			starlette_app = self.sse_app()
		await self._mcp_server.register_to_nacos("sse", self.settings.port, self.settings.sse_path)
		config = uvicorn.Config(
				starlette_app,
				host=self.settings.host,
				port=self.settings.port,
				log_level=self.settings.log_level.lower(),
		)
		server = uvicorn.Server(config)
		await server.serve()

