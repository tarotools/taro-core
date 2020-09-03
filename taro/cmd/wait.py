import signal

import sys

from taro import ExecutionStateObserver, JobInfo, ps
from taro.listening import StateReceiver


def run(args):
    receiver = StateReceiver(args.inst, args.states)
    receiver.listeners.append(lambda job_info: ps.print_state_change(job_info))
    receiver.listeners.append(StoppingListener(receiver, args.count))
    signal.signal(signal.SIGTERM, lambda _, __: _stop_server_and_exit(receiver, signal.SIGTERM))
    signal.signal(signal.SIGINT, lambda _, __: _stop_server_and_exit(receiver, signal.SIGINT))
    receiver.start()


def _stop_server_and_exit(server, signal_number: int):
    server.stop()
    sys.exit(128 + signal_number)


class StoppingListener(ExecutionStateObserver):

    def __init__(self, server, count=1):
        self._server = server
        self.count = count

    def state_update(self, job_info: JobInfo):
        self.count -= 1
        if self.count <= 0:
            self._server.stop()
