"""
Execution framework defines an abstraction for an execution of a task.
It consists of:
 1. Possible states of execution
 2. A structure for conveying of error conditions
 3. An interface for implementing various types of executions
"""

import abc
import datetime
from collections import OrderedDict
from enum import Enum, auto
from typing import Tuple, List, Iterable, Set, Optional


class ExecutionStateGroup(Enum):
    BEFORE_EXECUTION = auto()
    EXECUTING = auto()
    TERMINAL = auto()
    NOT_EXECUTED = auto()
    FAILURE = auto()


class ExecutionState(Enum):
    NONE = {}
    CREATED = {ExecutionStateGroup.BEFORE_EXECUTION}

    DISABLED = {ExecutionStateGroup.TERMINAL}

    PENDING = {ExecutionStateGroup.BEFORE_EXECUTION}  # Until released
    WAITING = {ExecutionStateGroup.BEFORE_EXECUTION}  # For another job
    # ON_HOLD or same as pending?

    TRIGGERED = {ExecutionStateGroup.EXECUTING}  # Start request sent, start confirmation not (yet) received
    STARTED = {ExecutionStateGroup.EXECUTING}
    RUNNING = {ExecutionStateGroup.EXECUTING}

    COMPLETED = {ExecutionStateGroup.TERMINAL}
    STOPPED = {ExecutionStateGroup.TERMINAL}

    CANCELLED = {ExecutionStateGroup.TERMINAL, ExecutionStateGroup.NOT_EXECUTED}
    SKIPPED = {ExecutionStateGroup.TERMINAL, ExecutionStateGroup.NOT_EXECUTED}
    SUSPENDED = {ExecutionStateGroup.TERMINAL, ExecutionStateGroup.NOT_EXECUTED}  # Temporarily disabled

    START_FAILED = {ExecutionStateGroup.TERMINAL, ExecutionStateGroup.FAILURE}
    INTERRUPTED = {ExecutionStateGroup.TERMINAL, ExecutionStateGroup.FAILURE}
    FAILED = {ExecutionStateGroup.TERMINAL, ExecutionStateGroup.FAILURE}
    ERROR = {ExecutionStateGroup.TERMINAL, ExecutionStateGroup.FAILURE}

    def __new__(cls, *args, **kwds):
        value = len(cls.__members__) + 1
        obj = object.__new__(cls)
        obj._value_ = value
        return obj

    def __init__(self, groups: Set[ExecutionStateGroup]):
        self.groups = groups

    def is_before_execution(self):
        return ExecutionStateGroup.BEFORE_EXECUTION in self.groups

    def is_executing(self):
        return ExecutionStateGroup.EXECUTING in self.groups

    def is_terminal(self) -> bool:
        return ExecutionStateGroup.TERMINAL in self.groups

    def is_failure(self) -> bool:
        return ExecutionStateGroup.FAILURE in self.groups


class ExecutionError(Exception):

    @classmethod
    def from_unexpected_error(cls, e: Exception):
        return cls("Unexpected error", ExecutionState.ERROR, unexpected_error=e)

    def __init__(self, message: str, exec_state: ExecutionState, unexpected_error: Exception = None, **kwargs):
        if not exec_state.is_failure():
            raise ValueError('exec_state must be a failure', exec_state)
        super().__init__(message)
        self.message = message
        self.exec_state = exec_state
        self.unexpected_error = unexpected_error
        self.params = kwargs


class Execution(abc.ABC):

    @abc.abstractmethod
    def is_async(self) -> bool:
        """
        SYNCHRONOUS TASK
            - finishes after the call of the execute() method
            - execution state is changed to RUNNING before the call of the execute() method

        ASYNCHRONOUS TASK
            - need not to finish after the call of the execute() method
            - execution state is changed to TRIGGER before the call of the execute() method

        :return: whether this execution is asynchronous
        """

    @abc.abstractmethod
    def execute(self) -> ExecutionState:
        """
        Executes a task

        :return: state after the execution of this method
        :raises ExecutionError: when execution failed
        :raises Exception: on unexpected failure
        """

    @abc.abstractmethod
    def status(self):
        """
        If progress monitoring is not supported then this method must return None

        :return: Current progress if executing or result when finished or None when not supported
        """

    @abc.abstractmethod
    def stop(self):
        """
        If not yet executed: Do not execute
        If already executing: Stop running execution GRACEFULLY
        If execution finished: Ignore
        """

    @abc.abstractmethod
    def interrupt(self):
        """
        If not yet executed: Do not execute
        If already executing: Stop running execution IMMEDIATELY
        If execution finished: Ignore
        """


class ExecutionLifecycle:

    def __init__(self, *state_changes: Tuple[ExecutionState, datetime.datetime]):
        self._state_changes: OrderedDict[ExecutionState, datetime.datetime] = OrderedDict(state_changes)

    def __copy__(self):
        copied = ExecutionLifecycle()
        copied._state_changes = self._state_changes
        return copied

    def __deepcopy__(self, memo):
        return ExecutionLifecycle(*self.state_changes())

    def state(self):
        return next(reversed(self._state_changes.keys()), ExecutionState.NONE)

    def states(self) -> List[ExecutionState]:
        return list(self._state_changes.keys())

    def state_changes(self) -> Iterable[Tuple[ExecutionState, datetime.datetime]]:
        return ((state, changed) for state, changed in self._state_changes.items())

    def changed(self, state: ExecutionState) -> datetime.datetime:
        return self._state_changes[state]

    def last_changed(self):
        return next(reversed(self._state_changes.values()), None)

    def executed(self):
        return self.execution_started() is not None

    def execution_started(self) -> Optional[datetime.datetime]:
        return next((changed for state, changed in self._state_changes.items() if state.is_executing()), None)

    def execution_finished(self) -> Optional[datetime.datetime]:
        state = self.state()
        if not state.is_terminal():
            return None
        return self.changed(state)

    def execution_time(self) -> Optional[datetime.timedelta]:
        finished = self.execution_finished()
        if not finished:
            return None
        started = self.execution_started()
        if not started:
            return None

        return finished - started


class ExecutionLifecycleManagement(ExecutionLifecycle):

    def __init__(self, *state_changes: Tuple[ExecutionState, datetime.datetime]):
        super().__init__(*state_changes)

    def set_state(self, new_state) -> bool:
        if not new_state or new_state == ExecutionState.NONE or self.state() == new_state:
            return False
        else:
            self._state_changes[new_state] = datetime.datetime.now(datetime.timezone.utc)
            return True
