"""PowerShell tool — shell/command execution."""

import asyncio

from mcp.types import ToolAnnotations
from windows_mcp.infrastructure import with_analytics
from windows_mcp.powershell import PowerShellExecutor
from fastmcp import Context

# Extra headroom added to the asyncio-side timeout on top of the PowerShell
# command's own timeout, so the python-side watchdog does not race the
# process-side graceful timeout under normal conditions.
_ASYNC_TIMEOUT_SLACK_SECONDS = 10


def register(mcp, *, get_desktop, get_analytics):
    @mcp.tool(
        name="PowerShell",
        description="Shell/command execution. Keywords: shell, run, execute, cmd, terminal, command line, script. A comprehensive system tool for executing any PowerShell commands. Use it to navigate the file system, manage files and processes, and execute system-level operations. Capable of accessing web content (e.g., via Invoke-WebRequest), interacting with network resources, and performing complex administrative tasks. This tool provides full access to the underlying operating system capabilities, making it the primary interface for system automation, scripting, and deep system interaction.",
        annotations=ToolAnnotations(
            title="PowerShell",
            readOnlyHint=False,
            destructiveHint=True,
            idempotentHint=False,
            openWorldHint=True,
        ),
    )
    @with_analytics(get_analytics(), "Powershell-Tool")
    async def powershell_tool(command: str, timeout: int = 30, ctx: Context = None) -> str:
        try:
            # Run the blocking subprocess call on a worker thread so the
            # event loop stays free to service other concurrent tool calls.
            # A python-side timeout (command timeout + slack) bounds the
            # thread call itself in case the graceful-timeout logic inside
            # execute_command ever fails to return.
            response, status_code = await asyncio.wait_for(
                asyncio.to_thread(PowerShellExecutor.execute_command, command, timeout),
                timeout=timeout + _ASYNC_TIMEOUT_SLACK_SECONDS,
            )
            return f"Response: {response}\nStatus Code: {status_code}"
        except asyncio.TimeoutError:
            raise TimeoutError(
                f"PowerShell command did not complete within {timeout + _ASYNC_TIMEOUT_SLACK_SECONDS}s "
                "(python-side watchdog)."
            )
        except Exception as e:
            raise
