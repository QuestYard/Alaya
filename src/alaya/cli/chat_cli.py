"""Alaya CLI Chat Interactive Tool."""

import asyncio
import os
import typer
from rich.console import Console
from rich.panel import Panel
from rich.text import Text
from pydantic_ai.messages import (
    ModelMessage,
    PartDeltaEvent,
    FunctionToolCallEvent,
    FunctionToolResultEvent,
    TextPartDelta,
    ThinkingPartDelta,
)

from .. import conf, logger, hurag
from ..models import User
from ..agents import (
    get_agent,
    AgentDeps,
    compress_history_if_needed,
    estimate_tokens,
    get_context_limit,
)

app = typer.Typer(help="Alaya Agent CLI Interactive Workbench", add_completion=False)
console = Console()


def render_banner(user: User) -> None:
    """Render the welcome banner and status in Copilot CLI style."""
    model_name = os.getenv("DEEPSEEK_MODEL", "deepseek-v4-flash")
    ctx_size = getattr(conf.app, "ctx_size", "large")
    ctx_limit = get_context_limit()

    info_text = Text()
    info_text.append("✨ Alaya Knowledge Agent CLI\n", style="bold cyan")
    info_text.append("━" * 50 + "\n", style="dim")
    info_text.append("  • 用户身份: ", style="dim")
    info_text.append(f"{user.username} ({user.account})\n", style="bold white")
    info_text.append("  • 组织路径: ", style="dim")
    info_text.append(f"{user.user_path}\n", style="bold yellow")
    info_text.append("  • 语言模型: ", style="dim")
    info_text.append(f"{model_name}\n", style="bold green")
    info_text.append("  • 上下文规模: ", style="dim")
    info_text.append(f"{ctx_size} (~{ctx_limit} tokens)\n", style="bold magenta")
    info_text.append("━" * 50 + "\n", style="dim")
    info_text.append("常用命令: ", style="dim")
    info_text.append("/new", style="bold yellow")
    info_text.append(" 开启新会话  |  ", style="dim")
    info_text.append("/clear", style="bold yellow")
    info_text.append(" 清屏  |  ", style="dim")
    info_text.append("/tokens", style="bold yellow")
    info_text.append(" 查看Token  |  ", style="dim")
    info_text.append("/exit", style="bold yellow")
    info_text.append(" 退出", style="dim")

    console.print(Panel(info_text, border_style="cyan", padding=(0, 1)))


def render_help() -> None:
    """Render help menu for slash commands."""
    help_text = Text()
    help_text.append("Available Commands:\n", style="bold white")
    help_text.append("  /new     - 开启新的一轮会话，清空历史消息\n", style="yellow")
    help_text.append("  /clear   - 清除当前终端屏幕\n", style="yellow")
    help_text.append(
        "  /tokens  - 查看当前会话累计的消息轮数与估算 Token 使用量\n",
        style="yellow",
    )
    help_text.append("  /help    - 查看命令帮助信息\n", style="yellow")
    help_text.append(
        "  /exit    - 退出当前 CLI 工具 (快捷键: Ctrl+C / Ctrl+D)\n",
        style="yellow",
    )
    console.print(Panel(help_text, title="Help", border_style="dim", padding=(0, 1)))


async def run_chat_loop() -> None:
    """Async main loop for interactive chat session."""
    user_path = os.getenv("CLI_USER_PATH", "/questyard")
    cli_user = User(
        id="cli_virtual_user",
        account="cli_user",
        username="CLI测试用户",
        user_path=user_path,
    )

    render_banner(cli_user)

    agent = get_agent()
    http_client = await hurag.get_client()
    deps = AgentDeps(user=cli_user, client=http_client)

    message_history: list[ModelMessage] = []

    try:
        while True:
            try:
                user_input = console.input(
                    "\n[bold #38bdf8]You[/bold #38bdf8] [dim]>[/dim] "
                ).strip()
            except (EOFError, KeyboardInterrupt):
                console.print("\n[dim]👋 再见！[/dim]")
                break

            if not user_input:
                continue

            # Handle slash commands
            cmd = user_input.lower()
            if cmd in {"/exit", "/quit"}:
                console.print("[dim]👋 再见！[/dim]")
                break
            elif cmd == "/new":
                message_history.clear()
                console.print(
                    "[bold yellow]🔄 已重置会话，开启新一轮对话。[/bold yellow]"
                )
                continue
            elif cmd == "/clear":
                console.clear()
                render_banner(cli_user)
                continue
            elif cmd == "/help":
                render_help()
                continue
            elif cmd == "/tokens":
                est = estimate_tokens(message_history)
                limit = get_context_limit()
                console.print(
                    f"[dim]当前历史消息数: {len(message_history)} 条 | "
                    f"估算 Token 消耗: {est} / {limit} ({(est/limit*100):.1f}%)[/dim]"
                )
                continue

            # Context window compression check before sending prompt
            message_history, was_compressed = compress_history_if_needed(
                message_history
            )
            if was_compressed:
                console.print(
                    "[dim italic]ℹ 检测到历史上下文接近上限，已自动压缩早期会话。"
                    "[/dim italic]"
                )

            # Stream response from Agent
            try:
                async with agent.run_stream_events(
                    user_input,
                    deps=deps,
                    message_history=message_history,
                ) as events:
                    thinking_started = False
                    text_started = False

                    async for event in events:
                        # 1. Tool Call Notification
                        if isinstance(event, FunctionToolCallEvent):
                            args_repr = str(event.part.args) if event.part.args else ""
                            if len(args_repr) > 120:
                                args_repr = args_repr[:117] + "..."
                            console.print(
                                f"\n[bold cyan]⚡ Tool Call:[/bold cyan] "
                                f"[bold white]{event.part.tool_name}[/bold white] "
                                f"[dim]({args_repr})[/dim]"
                            )
                        # 2. Tool Completed Notification (Suppress tool return value)
                        elif isinstance(event, FunctionToolResultEvent):
                            console.print(
                                f"[bold green]✔ Tool Completed:[/bold green] "
                                f"[bold white]{event.part.tool_name}[/bold white]"
                            )
                        # 3. Stream Deltas (Thinking & Text)
                        elif isinstance(event, PartDeltaEvent):
                            if isinstance(event.delta, ThinkingPartDelta):
                                if not thinking_started:
                                    console.print(
                                        "\n[bold dim cyan]🧠 Thinking[/bold dim cyan]"
                                    )
                                    thinking_started = True
                                console.print(
                                    event.delta.content_delta,
                                    style="dim italic",
                                    end="",
                                )
                            elif isinstance(event.delta, TextPartDelta):
                                if not text_started:
                                    if thinking_started:
                                        console.print()
                                    console.print("\n[bold green]● Alaya[/bold green]")
                                    text_started = True
                                console.print(event.delta.content_delta, end="")

                    console.print()
                    # Update conversation history with all messages from this run
                    message_history = events.all_messages()

            except Exception as e:
                logger.error(f"Error during agent run: {e}", exc_info=True)
                console.print(f"\n[bold red]❌ 执行出错:[/bold red] {e}")

    finally:
        await hurag.close_client()


@app.command()
def chat(
    user_path: str = typer.Option(
        None,
        "--user-path",
        "-u",
        help="覆盖环境变量 CLI_USER_PATH 指定的虚拟用户组织路径",
    ),
) -> None:
    """启动 Alaya 知识库 Agent CLI 交互式测试工作台。"""
    if user_path:
        os.environ["CLI_USER_PATH"] = user_path

    try:
        asyncio.run(run_chat_loop())
    except KeyboardInterrupt:
        console.print("\n[dim]👋 退出会话。[/dim]")


def main() -> None:
    """Console script entrypoint."""
    app()


if __name__ == "__main__":
    app()
