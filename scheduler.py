import asyncio
import time
from typing import Callable, List

from nextcord.ext import commands, tasks

from variables import bot


class ScheduledTask:
	def __init__(self, wait_time, callable_, args, kwargs):
		self.at = time.time() + wait_time
		self.callable = callable_
		self.args = args
		self.kwargs = kwargs
		self._cancelled = False

	async def __call__(self):
		if asyncio.iscoroutinefunction(self.callable):
			await self.callable(*self.args, **self.kwargs)
		else:
			self.callable(*self.args, **self.kwargs)

	def cancel(self):
		self._cancelled = True

	def is_cancelled(self):
		return self._cancelled


scheduled_tasks: List[ScheduledTask] = []


def run_task_later(wait_time: int, callable_: Callable, *args, **kwargs) -> ScheduledTask:
	task = ScheduledTask(wait_time, callable_, args, kwargs)
	scheduled_tasks.append(task)
	return task


class SchedulerCog(commands.Cog):
	@commands.Cog.listener()
	async def on_first_ready(self):
		self.scheduler_loop.start()

	@tasks.loop(seconds=1)
	async def scheduler_loop(self):
		t = time.time()
		for task in scheduled_tasks.copy():
			if task.is_cancelled():
				scheduled_tasks.remove(task)
				continue
			if task.at <= t:
				bot.loop.create_task(task())
				scheduled_tasks.remove(task)
