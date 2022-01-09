"""
Job framework defines components used for job submission and management.
It is built upon :mod:`execution` framework.
It provides constructs for:
  1. Creating of job definition
  2. Implementing of job instance
  3. Implementing of job observer

There are two type of clients of the framework:
  1. Job users
  2. Job management implementation
"""

import abc
from collections import namedtuple
from fnmatch import fnmatch

from taro.jobs.execution import ExecutionError


class JobInstance(abc.ABC):

    @property
    @abc.abstractmethod
    def job_id(self) -> str:
        """Identifier of the job of this instance"""

    @property
    @abc.abstractmethod
    def instance_id(self) -> str:
        """Identifier of this instance"""

    @property
    @abc.abstractmethod
    def lifecycle(self):
        """Execution lifecycle of this instance"""

    @property
    @abc.abstractmethod
    def status(self):
        """Current status of the job or None if not supported"""

    @property
    @abc.abstractmethod
    def last_output(self):
        """Last lines of output or None if not supported"""

    @property
    @abc.abstractmethod
    def warnings(self):
        """
        Return dictionary of {alarm_name: occurrence_count}

        :return: warnings
        """

    @abc.abstractmethod
    def add_warning(self, warning):
        """
        Add warning to the instance

        :param warning warning to add
        """

    @property
    @abc.abstractmethod
    def exec_error(self) -> ExecutionError:
        """Job execution error if occurred otherwise None"""

    @abc.abstractmethod
    def create_info(self):
        """
        Create consistent (thread-safe) snapshot of job instance state

        :return job (instance) info
        """

    @abc.abstractmethod
    def stop(self):
        """
        Stop running execution gracefully
        """

    @abc.abstractmethod
    def interrupt(self):
        """
        Stop running execution immediately
        """

    @abc.abstractmethod
    def add_state_observer(self, observer):
        """
        Register execution state observer
        Observer can be:
            1. An instance of ExecutionStateObserver
            2. Callable object with single parameter of JobInfo type

        :param observer observer to register
        """

    @abc.abstractmethod
    def remove_state_observer(self, observer):
        """
        De-register execution state observer

        :param observer observer to de-register
        """

    @abc.abstractmethod
    def add_warning_observer(self, observer):
        """
        Register warning observer

        :param observer observer to register
        """

    @abc.abstractmethod
    def remove_warning_observer(self, observer):
        """
        De-register warning observer

        :param observer observer to de-register
        """

    @abc.abstractmethod
    def add_output_observer(self, observer):
        """
        Register output observer

        :param observer observer to register
        """

    @abc.abstractmethod
    def remove_output_observer(self, observer):
        """
        De-register output observer

        :param observer observer to de-register
        """


class JobInfo:
    """
    Immutable snapshot of job instance state
    """

    def __init__(self, job_id: str, instance_id: str, lifecycle, status, warnings, exec_error: ExecutionError):
        self._job_id = job_id
        self._instance_id = instance_id
        self._lifecycle = lifecycle
        self._status = status
        self._warnings = warnings
        self._exec_error = exec_error

    @property
    def job_id(self) -> str:
        return self._job_id

    @property
    def instance_id(self) -> str:
        return self._instance_id

    @property
    def lifecycle(self):
        return self._lifecycle

    @property
    def state(self):
        return self._lifecycle.state()

    @property
    def status(self):
        return self._status

    @property
    def warnings(self):
        return self._warnings

    @property
    def exec_error(self) -> ExecutionError:
        return self._exec_error

    def matches(self, instance, job_matching_strategy=fnmatch):
        return job_matching_strategy(self.job_id, instance) or fnmatch(self.instance_id, instance)

    def __repr__(self) -> str:
        return "{}({!r}, {!r}, {!r}, {!r}, {!r}, {!r})".format(
            self.__class__.__name__, self._job_id, self.instance_id, self._lifecycle, self._status, self._warnings,
            self._exec_error)


class JobInfoCollection:

    def __init__(self, jobs=list()):
        self._jobs = jobs

    @property
    def jobs(self):
        return self._jobs

    def append(self, item):
        self._jobs.append(item)


class ExecutionStateObserver(abc.ABC):

    @abc.abstractmethod
    def state_update(self, job_info: JobInfo):
        """This method is called when job instance execution state is changed."""


DisabledJob = namedtuple('DisabledJob', 'job_id regex created expires')

Warn = namedtuple('Warn', 'name params')
WarnEventCtx = namedtuple('WarnEventCtx', 'count')


class WarningObserver(abc.ABC):

    @abc.abstractmethod
    def new_warning(self, job_info: JobInfo, warning: Warn, event_ctx: WarnEventCtx):
        """This method is called when there is a new warning event."""


class JobOutputObserver(abc.ABC):

    @abc.abstractmethod
    def output_update(self, job_info: JobInfo, output):
        """Executed when new output line is available."""
