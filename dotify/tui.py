"""Rich terminal UI for selection, queue progress, speed, ETA, and summary."""

from __future__ import annotations

import asyncio
import math
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from InquirerPy import inquirer
from InquirerPy.base.control import Choice
from rich.console import Console
from rich.filesize import decimal
from rich.progress import (
    BarColumn,
    DownloadColumn,
    Progress,
    SpinnerColumn,
    TaskProgressColumn,
    TextColumn,
    TimeRemainingColumn,
    TransferSpeedColumn,
)
from rich.table import Table

from .downloader.progress import DownloadProgress
from .i18n import Translator


@dataclass(slots=True)
class DownloadSummary:
    success: int = 0
    skipped: int = 0
    failed: int = 0
    transferred_bytes: int = 0
    formats: dict[str, int] = field(default_factory=dict)
    fallbacks: list[tuple[str, str, str, str]] = field(default_factory=list)


class TerminalUI:
    def __init__(
        self,
        translator: Translator,
        console: Console | None = None,
        interactive: bool | None = None,
    ) -> None:
        self.translator = translator
        self.console = console or Console()
        self.interactive = (
            self.console.is_terminal and sys.stdin.isatty()
            if interactive is None
            else interactive
        )
        self.progress = Progress(
            SpinnerColumn(),
            TextColumn("{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            DownloadColumn(),
            TransferSpeedColumn(),
            TimeRemainingColumn(),
            console=self.console,
            transient=False,
        )
        self.summary = DownloadSummary()
        self.started_at = time.monotonic()
        self._task_ids: dict[int, int] = {}
        self._item_labels: dict[int, str] = {}
        self._current_item_id: int | None = None
        self._loop: asyncio.AbstractEventLoop | None = None
        self._started = False

    async def select_items(self, items: list[Any]) -> list[Any]:
        if len(items) <= 1 or not self.interactive:
            return items
        choices = [
            Choice(value=index, name=self.item_label(item, index + 1), enabled=True)
            for index, item in enumerate(items)
        ]
        selected_indices = await inquirer.checkbox(
            message=self.translator("select_media"),
            choices=choices,
            cycle=True,
        ).execute_async()
        return [items[index] for index in selected_indices]

    async def select_playlist_mode(self) -> str:
        """Choose streaming-all or explicit track selection for a playlist."""

        if not self.interactive:
            return "all"
        return await inquirer.select(
            message=self.translator("playlist_action"),
            choices=[
                Choice(
                    value="all",
                    name=self.translator("playlist_download_all"),
                ),
                Choice(
                    value="select",
                    name=self.translator("playlist_choose_tracks"),
                ),
            ],
            default="all",
            cycle=True,
        ).execute_async()

    def show_streaming_queue(self) -> None:
        self.console.print(
            f"[cyan]{self.translator('playlist_streaming_all')}[/cyan]"
        )

    def add_item(self, item: Any, index: int) -> None:
        task_id = self.progress.add_task(
            self.item_label(item, index),
            total=None,
            start=False,
        )
        self._task_ids[id(item)] = task_id
        self._item_labels[id(item)] = self.item_label(item, 0, include_index=False)

    def show_queue(self, items: list[Any]) -> None:
        if not items:
            self.console.print(f"[yellow]{self.translator('queue_empty')}[/yellow]")
            return
        table = Table(title=self.translator("queue_title"), show_lines=False)
        table.add_column("#", justify="right", style="dim")
        table.add_column("Media")
        table.add_column("Status", style="cyan")
        for index, item in enumerate(items, start=1):
            table.add_row(
                str(index),
                self.item_label(item, index, include_index=False),
                self.translator("status_waiting"),
            )
        self.console.print(table)

    def add_items(self, items: list[Any]) -> None:
        for index, item in enumerate(items, start=1):
            self.add_item(item, index)

    def start(self, items: list[Any] | None = None) -> None:
        if items:
            self.add_items(items)
        if self._started or not self._task_ids:
            return
        self._loop = asyncio.get_running_loop()
        self.progress.start()
        self._started = True

    def start_item(self, item: Any) -> None:
        self._current_item_id = id(item)
        task_id = self._task_ids.get(id(item))
        if task_id is not None:
            self.progress.start_task(task_id)
            self.progress.update(
                task_id,
                description=f"[cyan]{self.translator('status_downloading')}[/cyan] "
                f"{self.item_label(item, 0, include_index=False)}",
            )

    async def wait_for_widevine_retry(
        self,
        delay: float,
        retry: int,
        total_retries: int,
    ) -> None:
        """Show an item-level 429 countdown while preserving the retry delay."""

        item_id = self._current_item_id
        task_id = self._task_ids.get(item_id) if item_id is not None else None
        label = self._item_labels.get(item_id, "") if item_id is not None else ""
        remaining = max(0.0, delay)
        while remaining > 0:
            if task_id is not None and self._current_item_id == item_id:
                self.progress.update(
                    task_id,
                    description=(
                        f"[yellow]{self.translator('status_rate_limited')}[/yellow] "
                        f"{label} — "
                        + self.translator(
                            "rate_limit_countdown",
                            seconds=math.ceil(remaining),
                            retry=retry,
                            total=total_retries,
                        )
                    ),
                )
            step = min(1.0, remaining)
            await asyncio.sleep(step)
            remaining -= step

        if task_id is not None and self._current_item_id == item_id:
            self.progress.update(
                task_id,
                description=(
                    f"[cyan]{self.translator('status_downloading')}[/cyan] {label}"
                ),
            )

    def on_progress(self, payload: dict[str, Any] | DownloadProgress) -> None:
        event = (
            payload
            if isinstance(payload, DownloadProgress)
            else DownloadProgress.from_ytdlp(payload)
        )
        try:
            running_loop = asyncio.get_running_loop()
        except RuntimeError:
            running_loop = None
        if running_loop is self._loop:
            self._apply_progress(event)
        elif self._loop and self._loop.is_running():
            self._loop.call_soon_threadsafe(self._apply_progress, event)
        else:
            self._apply_progress(event)

    def _apply_progress(self, event: DownloadProgress) -> None:
        if self._current_item_id is None:
            return
        task_id = self._task_ids.get(self._current_item_id)
        if task_id is None:
            return
        update: dict[str, Any] = {"completed": event.downloaded_bytes}
        if event.total_bytes:
            update["total"] = event.total_bytes
        self.progress.update(task_id, **update)

    def finish_item(self, item: Any, status: str) -> None:
        if status == "success":
            self.summary.success += 1
        elif status == "skipped":
            self.summary.skipped += 1
        else:
            self.summary.failed += 1

        final_path = getattr(item, "final_path", None)
        audio_description = getattr(item, "audio_description", None)
        fallback_description = getattr(item, "fallback_audio_description", None)
        if status == "success" and final_path and Path(final_path).is_file():
            self.summary.transferred_bytes += Path(final_path).stat().st_size
        if status == "success" and audio_description:
            self.summary.formats[audio_description] = (
                self.summary.formats.get(audio_description, 0) + 1
            )
            if fallback_description:
                self.summary.fallbacks.append(
                    (
                        self.item_label(item, 0, include_index=False),
                        fallback_description,
                        audio_description,
                        final_path or "-",
                    )
                )

        task_id = self._task_ids.get(id(item))
        if task_id is not None:
            task = next(task for task in self.progress.tasks if task.id == task_id)
            completed = task.completed
            total = task.total or completed or 1
            style = {
                "success": "green",
                "skipped": "yellow",
                "failed": "red",
            }[status]
            format_suffix = (
                f" [dim]({audio_description})[/dim]"
                if status == "success" and audio_description
                else ""
            )
            self.progress.update(
                task_id,
                completed=total,
                total=total,
                description=f"[{style}]{self.translator(f'status_{status}')}[/{style}] "
                f"{self.item_label(item, 0, include_index=False)}{format_suffix}",
            )
            self.progress.stop_task(task_id)
        self._current_item_id = None

    def close(self) -> DownloadSummary:
        if self._started:
            self.progress.stop()
            self._started = False
        self.print_summary()
        return self.summary

    def print_summary(self) -> None:
        elapsed = time.monotonic() - self.started_at
        table = Table(title=self.translator("summary_title"), show_header=False)
        table.add_column("Metric", style="bold")
        table.add_column("Value", justify="right")
        table.add_row(self.translator("summary_success"), f"[green]{self.summary.success}[/green]")
        table.add_row(self.translator("summary_skipped"), f"[yellow]{self.summary.skipped}[/yellow]")
        table.add_row(self.translator("summary_failed"), f"[red]{self.summary.failed}[/red]")
        table.add_row(self.translator("summary_duration"), format_duration(elapsed))
        table.add_row(
            self.translator("summary_bytes"),
            decimal(self.summary.transferred_bytes),
        )
        if self.summary.formats:
            formats = ", ".join(
                f"{name} ×{count}" for name, count in self.summary.formats.items()
            )
            table.add_row(self.translator("summary_formats"), formats)
        self.console.print(table)
        if self.summary.fallbacks:
            fallback_table = Table(title=self.translator("fallback_title"))
            fallback_table.add_column(self.translator("fallback_media"))
            fallback_table.add_column(self.translator("fallback_requested"))
            fallback_table.add_column(self.translator("fallback_actual"))
            fallback_table.add_column(self.translator("fallback_path"))
            for fallback in self.summary.fallbacks:
                fallback_table.add_row(*fallback)
            self.console.print(fallback_table)
            for media, _requested, _actual, path in self.summary.fallbacks:
                self.console.print(
                    f"[bold]{self.translator('fallback_path')} ({media}):[/bold] {path}",
                    overflow="fold",
                )

    @staticmethod
    def item_label(item: Any, index: int, include_index: bool = True) -> str:
        media = getattr(item, "media", None)
        metadata = getattr(media, "media_metadata", {}) or {}
        tags = getattr(media, "tags", None)
        title = metadata.get("name") or getattr(tags, "title", None) or "Unknown"
        artist = getattr(tags, "artist", None)
        label = f"{artist} — {title}" if artist else title
        return f"{index}. {label}" if include_index else label


def format_duration(seconds: float) -> str:
    seconds = max(0, int(seconds))
    minutes, seconds = divmod(seconds, 60)
    hours, minutes = divmod(minutes, 60)
    if hours:
        return f"{hours:d}:{minutes:02d}:{seconds:02d}"
    return f"{minutes:02d}:{seconds:02d}"
