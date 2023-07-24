from multiprocessing import Queue
from pathlib import Path
from typing import Dict, Tuple

import yaml

from tarotools.taro import paths, JobInst, Warn, WarningObserver, ExecutionStateObserver
from tarotools.taro import cfg
from tarotools.taro.jobs.inst import WarnEventCtx


def reset_config():
    cfg.log_mode = cfg.DEF_LOG
    cfg.log_stdout_level = cfg.DEF_LOG_STDOUT_LEVEL
    cfg.log_file_level = cfg.DEF_LOG_FILE_LEVEL
    cfg.log_file_path = cfg.DEF_LOG_FILE_PATH

    cfg.persistence_enabled = cfg.DEF_PERSISTENCE_ENABLED
    cfg.persistence_type = cfg.DEF_PERSISTENCE_TYPE
    cfg.persistence_database = cfg.DEF_PERSISTENCE_DATABASE

    cfg.plugins = cfg.DEF_PLUGINS


def create_test_config(config):
    create_custom_test_config(paths.CONFIG_FILE, config)


def create_custom_test_config(filename, config):
    path = _custom_test_config_path(filename)
    with open(path, 'w') as outfile:
        yaml.dump(config, outfile, default_flow_style=False)
    return path


def remove_test_config():
    remove_custom_test_config(paths.CONFIG_FILE)


def remove_custom_test_config(filename):
    config = _custom_test_config_path(filename)
    if config.exists():
        config.unlink()


def _test_config_path() -> Path:
    return _custom_test_config_path(paths.CONFIG_FILE)


def _custom_test_config_path(filename) -> Path:
    return Path.cwd() / filename


class StateWaiter:
    """
    This class is used for waiting for execution states of job executed in different process.

    See :class:`PutStateToQueueObserver`

    Attributes:
        state_queue The process must put execution states into this queue
    """

    def __init__(self):
        self.state_queue = Queue()

    def wait_for_state(self, state, timeout=1):
        while True:
            if state == self.state_queue.get(timeout=timeout):
                return


class PutStateToQueueObserver(ExecutionStateObserver):
    """
    This observer puts execution states into the provided queue. With multiprocessing queue this can be used for sending
    execution states into the parent process.

    See :class:`StateWaiter`
    """

    def __init__(self, queue):
        self.queue = queue

    def state_update(self, job_inst: JobInst):
        self.queue.put_nowait(job_inst.state)


class TestWarningObserver(WarningObserver):

    def __init__(self):
        self.warnings: Dict[str, Tuple[JobInst, Warn, WarnEventCtx]] = {}

    def new_warning(self, job_inst: JobInst, warning: Warn, event_ctx):
        self.warnings[warning.name] = (job_inst, warning, event_ctx)