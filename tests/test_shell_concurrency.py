"""Regression test for shell concurrency — PowerShell tool must not block the event loop."""

import asyncio
import time
from collections.abc import Callable

from windows_mcp.powershell import PowerShellExecutor
from windows_mcp.tools import shell


class FakeMCP:
    def __init__(self) -> None:
        self.tools: dict[str, Callable] = {}
        self.tool_options: dict[str, dict[str, object]] = {}

    def tool(self, *, name: str, **kwargs: object) -> Callable:
        self.tool_options[name] = kwargs

        def decorator(func: Callable) -> Callable:
            self.tools[name] = func
            return func

        return decorator


def test_powershell_tool_runs_concurrently(monkeypatch):
    def fake_execute_command(command, timeout):
        time.sleep(2)
        return "ok", 0

    monkeypatch.setattr(PowerShellExecutor, "execute_command", staticmethod(fake_execute_command))

    mcp = FakeMCP()
    shell.register(mcp, get_desktop=lambda: None, get_analytics=lambda: None)
    powershell_tool = mcp.tools["PowerShell"]

    async def run_two():
        start = time.monotonic()
        await asyncio.gather(
            powershell_tool(command="echo hi"),
            powershell_tool(command="echo hi"),
        )
        return time.monotonic() - start

    elapsed = asyncio.run(run_two())
    assert elapsed < 3.5, f"expected concurrent execution under 3.5s, got {elapsed:.2f}s"
