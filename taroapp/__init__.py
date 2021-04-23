import sys

from taro import persistence
from taro.persistence import PersistenceDisabledError
from taroapp import cmd, argsconfig, cli


def main_cli():
    main(None)


def main(args):
    """Taro CLI app main function.

    Note: Configuration is setup before execution of all commands although not all commands require it.
          This practice increases safety (in regards with future extensions) and consistency.
          Performance impact is expected to be negligible.

    :param args: CLI arguments
    """
    args_ns = cli.parse_args(args)

    """
    If config create command is chosen, config loading is skipped.
    """
    if not(args_ns.action == 'config' and args_ns.config_action == 'create'):
        setup_config(args_ns)
    
    try:
        cmd.run(args_ns)
    except PersistenceDisabledError:
        print('This command cannot be executed with disabled persistence. Enable persistence in config file first.',
              file=sys.stderr)
    finally:
        persistence.close()


def setup_config(args):
    """Load and setup config according to provided CLI arguments

    :param args: CLI arguments
    """
    argsconfig.load_config(args)
    argsconfig.override_config(args)
