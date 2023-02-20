import logging
from abc import ABC
from abc import abstractmethod
from collections import deque, OrderedDict
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Optional, Any, Sequence, Tuple

from taro import util
from taro.util import TimePeriod, format_dt_iso, parse_datetime

log = logging.getLogger(__name__)


class Progress(ABC):

    @property
    @abstractmethod
    def completed(self):
        pass

    @property
    @abstractmethod
    def total(self):
        pass

    @property
    @abstractmethod
    def unit(self):
        pass

    @property
    @abstractmethod
    def last_updated_at(self):
        pass

    @property
    def pct_done(self):
        if isinstance(self.completed, (int, float)) and isinstance(self.total, (int, float)):
            return self.completed / self.total
        else:
            return None

    @property
    def is_finished(self):
        return self.completed and self.total and (self.completed == self.total)

    def copy(self):
        return ProgressInfo(self.completed, self.total, self.unit, self.last_updated_at)

    def to_dict(self):
        return {
            'completed': self.completed,
            'total': self.total,
            'unit': self.unit,
            'last_updated_at': format_dt_iso(self.last_updated_at),
            'pct_done': self.pct_done,
            'is_finished': self.is_finished
        }

    def __str__(self):
        val = f"{self.completed or '?'}/{self.total or '?'}"
        if self.unit:
            val += f" {self.unit}"
        if pct_done := self.pct_done:
            val += f" ({round(pct_done * 100, 0):.0f}%)"

        return val


@dataclass(frozen=True)
class ProgressInfo(Progress):
    _completed: Any
    _total: Any
    _unit: str = ''
    _last_updated_at: datetime = None

    @classmethod
    def from_dict(cls, data):
        completed = data.get("completed", None)
        total = data.get("total", None)
        unit = data.get("unit", '')
        last_updated_at = util.parse_datetime(data.get("last_updated_at", None))
        return cls(completed, total, unit, last_updated_at)

    @property
    def completed(self):
        return self._completed

    @property
    def total(self):
        return self._total

    @property
    def unit(self):
        return self._unit

    @property
    def last_updated_at(self):
        return self._last_updated_at


class Operation(TimePeriod):

    @property
    @abstractmethod
    def name(self):
        pass

    @property
    @abstractmethod
    def progress(self):
        pass

    def copy(self):
        return OperationInfo(self.name, self.progress.copy(), self.started_at, self.ended_at)

    def to_dict(self):
        return {
            'name': self.name,
            'progress': self.progress.to_dict(),
            'started_at': format_dt_iso(self.started_at),
            'ended_at': format_dt_iso(self.ended_at)
        }

    def __str__(self):
        return f"{self.name} {self.progress}"


@dataclass(frozen=True)
class OperationInfo(Operation):
    _name: str
    _progress: Progress
    _started_at: datetime
    _ended_at: datetime

    @classmethod
    def from_dict(cls, data):
        name = data.get("name", None)
        if progress_data := data.get("progress", None):
            progress = ProgressInfo.from_dict(progress_data)
        else:
            progress = None
        started_at = util.parse_datetime(data.get("started_at", None))
        ended_at = util.parse_datetime(data.get("ended_at", None))
        return cls(name, progress, started_at, ended_at)

    @property
    def name(self):
        return self._name

    @property
    def progress(self):
        return self._progress

    @property
    def started_at(self):
        return self._started_at

    @property
    def ended_at(self):
        return self._ended_at


class TrackedTask(TimePeriod):

    @property
    @abstractmethod
    def name(self):
        pass

    @property
    @abstractmethod
    def events(self):
        pass

    @property
    @abstractmethod
    def last_event(self):
        pass

    @property
    @abstractmethod
    def operations(self):
        pass

    @property
    @abstractmethod
    def subtasks(self):
        pass

    def copy(self):
        return TrackedTaskInfo(
            self.name,
            self.events,
            [op.copy() for op in self.operations],
            [task.copy() for task in self.subtasks],
            self.started_at,
            self.ended_at)

    def to_dict(self):
        return {
            'name': self.name,
            'events': [(event, format_dt_iso(ts)) for event, ts in self.events],
            'operations': [op.to_dict() for op in self.operations],
            'subtasks': [task.to_dict() for task in self.subtasks],
            'started_at': format_dt_iso(self.started_at),
            'ended_at': format_dt_iso(self.ended_at),
        }

    def __str__(self):
        latest_op_dt = min((op.started_at for op in self.operations if op.started_at), default=None)
        if self.last_event and (latest_op_dt is None or (self.last_event[1] > latest_op_dt)):
            statuses = [f"{util.format_time_ms_local_tz(self.last_event[1])} {self.last_event[0]} "]
        else:
            statuses = []
        statuses += [op for op in self.operations if not op.progress.is_finished]
        return " | ".join((str(s) for s in statuses))


@dataclass(frozen=True)
class TrackedTaskInfo(TrackedTask):
    _name: str
    _events: Sequence[Tuple[str, datetime]]
    _operations: Sequence[Operation]
    _subtasks: Sequence[TrackedTask]
    _started_at: datetime
    _ended_at: datetime

    @classmethod
    def from_dict(cls, data):
        name = data.get("name", None)
        events = [(event, parse_datetime(ts)) for event, ts in data.get("events", ())]
        operations = [OperationInfo.from_dict(op) for op in data.get("operations", ())]
        subtasks = [TrackedTaskInfo.from_dict(task) for task in data.get("subtasks", ())]
        started_at = util.parse_datetime(data.get("started_at", None))
        ended_at = util.parse_datetime(data.get("ended_at", None))
        return cls(name, events, operations, subtasks, started_at, ended_at)

    @property
    def name(self):
        return self._name

    @property
    def events(self):
        return self._events

    @property
    def last_event(self):
        return self._events[-1] if self._events else None

    @property
    def operations(self):
        return self._operations

    @property
    def subtasks(self):
        return self._subtasks

    @property
    def started_at(self):
        return self._started_at

    @property
    def ended_at(self):
        return self._ended_at


class MutableTimePeriod(TimePeriod):

    def __init__(self):
        self._started_at = None
        self._ended_at = None

    @property
    def started_at(self):
        return self._started_at

    @property
    def ended_at(self):
        return self._ended_at


class MutableProgress(Progress):

    def __init__(self):
        self._completed = None
        self._total = None
        self._unit = ''
        self._last_updated_at = None

    @property
    def completed(self):
        return self._completed

    @property
    def total(self):
        return self._total

    @property
    def unit(self):
        return self._unit

    @property
    def last_updated_at(self):
        return self._last_updated_at

    def update(self, completed, total=None, unit: str = '', timestamp=None, *, increment=False):
        if self.completed and increment:
            self._completed += completed  # Must be a number if it's an increment
        else:
            self._completed = completed

        if total:
            self._total = total
        if unit:
            self._unit = unit
        self._last_updated_at = timestamp


class MutableOperation(Operation):

    def __init__(self, name):
        self._name = name
        self._started_at = None
        self._ended_at = None
        self._progress = MutableProgress()

    @property
    def name(self):
        return self._name

    @property
    def started_at(self):
        return self._started_at

    @property
    def ended_at(self):
        return self._ended_at

    @property
    def progress(self):
        return self._progress

    def update(self, completed, total=None, unit: str = '', timestamp=None, *, increment=False):
        if not self.started_at:
            self._started_at = timestamp

        self._progress.update(completed, total, unit, timestamp, increment=increment)

        if not self.ended_at and self.progress.is_finished:
            self._ended_at = timestamp


class MutableTrackedTask(TrackedTask):

    def __init__(self, name, max_events=100):
        self._name = name
        self._started_at = None
        self._ended_at = None
        self._events = deque(maxlen=max_events)
        self._operations = OrderedDict()
        self._subtasks = OrderedDict()

    @property
    def name(self):
        return self._name

    @property
    def started_at(self):
        return self._started_at

    @property
    def ended_at(self):
        return self._ended_at

    @property
    def events(self):
        return list(self._events)

    def add_event(self, name: str, timestamp=None):
        self._events.append((name, timestamp))

    @property
    def last_event(self) -> Optional[str]:
        if not self._events:
            return None
        return self._events[-1]

    def operation(self, name):
        op = self._operations.get(name)
        if not op:
            self._operations[name] = (op := MutableOperation(name))

        return op

    @property
    def operations(self):
        return list(self._operations.values())

    def subtask(self, name):
        task = self._subtasks.get(name)
        if not task:
            self._subtasks[name] = (task := MutableTrackedTask(name))

        return task

    @property
    def subtasks(self):
        return list(self._subtasks.values())


class Fields(Enum):
    EVENT = 'event'
    TASK = 'task'
    TIMESTAMP = 'timestamp'
    COMPLETED = 'completed'
    INCREMENT = 'increment'
    TOTAL = 'total'
    UNIT = 'unit'


DEFAULT_PATTERN = ''
