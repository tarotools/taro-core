import argparse
from argparse import RawTextHelpFormatter

from taro import cnf

ACTION_EXEC = 'exec'
ACTION_CONFIG = 'config'
ACTION_CONFIG_SHOW = 'show'

_true_options = ['yes', 'true', 't', 'y', '1', 'on']
_false_options = ['no', 'false', 'f', 'n', '0', 'off']
_all_boolean_options = _true_options + _false_options

_log_levels = ['critical', 'fatal', 'error', 'warn', 'warning', 'info', 'debug', 'off']


def parse_args(args):
    # TODO destination required
    parser = argparse.ArgumentParser(description='Manage your jobs with Taro')
    common = argparse.ArgumentParser()  # parent parser for subparsers in case they need to share common options
    subparsers = parser.add_subparsers(dest='action')  # command/action

    _init_exec_parser(common, subparsers)
    _init_ps_parser(common, subparsers)
    _init_show_config_parser(common, subparsers)

    parsed = parser.parse_args(args)
    _check_collisions(parser, parsed)
    return parsed


def _init_exec_parser(common, subparsers):
    """
    Creates parser for `exec` command

    :param common: parent parser
    :param subparsers: sub-parser for exec parser to be added to
    """

    exec_parser = subparsers.add_parser(
        'exec', formatter_class=RawTextHelpFormatter, parents=[common], description='Execute command', add_help=False)

    # General options
    exec_parser.add_argument('-dc', '--def-config', action='store_true', help='ignore config files and use defaults')
    exec_parser.add_argument('-C', '--config', type=str, help='path to custom config file')
    exec_parser.add_argument('--id', type=str, help='defines job ID')
    exec_parser.add_argument('-t', '--timeout', type=int)  # TODO implement

    # Config override options
    config_group = exec_parser.add_argument_group('config override', 'these options override entries from config file')
    config_group.add_argument('--log-enabled', type=_str2bool, metavar="{{{}}}".format(','.join(_all_boolean_options)),
                              help='overrides ' + cnf.LOG_ENABLED)
    config_group.add_argument('--log-stdout', type=str, choices=_log_levels,
                              help='overrides ' + cnf.LOG_STDOUT_LEVEL)
    config_group.add_argument('--log-file', type=str, choices=_log_levels,
                              help='overrides ' + cnf.LOG_FILE_LEVEL)
    config_group.add_argument('--log-file-path', type=str, metavar='PATH',
                              help='overrides ' + cnf.LOG_FILE_PATH)

    # Terms command and arguments taken from python doc and docker run help,
    # for this app (or rather exec command) these are operands (alternatively arguments)
    exec_parser.add_argument('command', type=str, metavar='COMMAND', help='program to execute')
    exec_parser.add_argument('arg', type=str, metavar='ARG', nargs=argparse.REMAINDER, help="program arguments")


def _init_ps_parser(common, subparsers):
    """
    Creates parsers for `ps` command

    :param common: parent parser
    :param subparsers: sub-parser for ps parser to be added to
    """

    ps_parser = subparsers.add_parser('ps', parents=[common], description='Show running jobs', add_help=False)


def _init_show_config_parser(common, subparsers):
    """
    Creates parsers for `config` command

    :param common: parent parser
    :param subparsers: sub-parser for config parser to be added to
    """

    config_parser = subparsers.add_parser('config', parents=[common], description='Config related actions',
                                          add_help=False)
    config_subparsers = config_parser.add_subparsers(dest='config_action')
    show_config_parser = config_subparsers.add_parser(
        'show', parents=[common], description='Print config used by exec command or config specified by an option',
        add_help=False)
    show_config_parser.add_argument('-dc', '--def-config', action='store_true', help='show default config')


# Maxim's solution: https://stackoverflow.com/questions/15008758
def _str2bool(v):
    if isinstance(v, bool):
        return v
    if v.lower() in _true_options:
        return True
    elif v.lower() in _false_options:
        return False
    else:
        raise argparse.ArgumentTypeError('Boolean value expected.')


def _check_collisions(parser, parsed):
    """
    Check that incompatible combinations of options were not used

    :param parser: parser
    :param parsed: parsed arguments
    """
    if hasattr(parsed, 'log_enabled') and parsed.log_enabled is not None and not parsed.log_enabled:
        for arg, val in vars(parsed).items():
            if arg != 'log_enabled' and arg.startswith('log_') and val is not None:
                parser.error("Conflicting options: log-enabled is set to false but {} is specified".format(arg))

    if hasattr(parsed, 'def_config') and hasattr(parsed, 'config') and parsed.def_config and parsed.config:
        parser.error('Conflicting options: both def-config and config specified')