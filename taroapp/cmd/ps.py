import json

from pygments import highlight
from pygments.formatters.terminal import TerminalFormatter
from pygments.lexers.data import JsonLexer

import taro.client
import taroapp.argsutil
from taro.jobs.job import JobInfoCollection
from taro.util import MatchingStrategy
from taroapp import printer
from taroapp.view import instance as view_inst


def run(args):
    instance_match = taroapp.argsutil.instance_matching_criteria(args, MatchingStrategy.PARTIAL)
    jobs = taro.client.read_jobs_info(instance_match).responses
    jobs = JobInfoCollection(*jobs)

    if args.format == 'table': 
        columns = view_inst.DEFAULT_COLUMNS
        if args.show_params:
            columns.insert(2, view_inst.PARAMETERS)
        printer.print_table(jobs.jobs, columns, show_header=True, pager=False)
    elif args.format == 'json':
        print(json.dumps({"jobs": [job.to_dict() for job in jobs.jobs]}))
    elif args.format == 'jsonp':
        json_str = json.dumps({"jobs": [job.to_dict() for job in jobs.jobs]}, indent=2)
        print(highlight(json_str, JsonLexer(), TerminalFormatter()))
    else:
        assert False, 'Unknown format: ' + args.format
