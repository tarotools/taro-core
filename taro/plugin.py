import importlib
import logging
import pkgutil
from inspect import signature
from typing import Dict

from taro.job import ExecutionStateObserver

log = logging.getLogger(__name__)


def discover_plugins(prefix, names) -> Dict[str, ExecutionStateObserver]:
    discovered = [name for finder, name, is_pkg in pkgutil.iter_modules() if name.startswith(prefix)]
    log.debug("event=[plugin_discovered] plugins=[%s]", ",".join(discovered))

    name2listener = {}
    for name in names:
        if name not in discovered:
            log.warning("event=[plugin_not_found] plugin=[%s]", name)
            continue

        try:
            module = importlib.import_module(name)
            listener = load_plugin(module)
            name2listener[name] = listener
            log.debug("event=[plugin_loaded] plugin=[%s] listener=[%s]", name, listener)
        except BaseException as e:
            log.exception("event=[invalid_plugin] plugin=[%s] reason=[%s]", name, e)

    return name2listener


def load_plugin(plugin_module):
    listener = plugin_module.create_execution_listener()  # Raises AttributeError if the method is missing
    if not listener:
        raise ValueError("listener cannot be None")
    update_method = listener.state_update  # Raises AttributeError if not 'state_update' method
    if not callable(update_method):
        raise AttributeError("plugin listener {} has no method 'state_update'".format(listener))
    state_update_sig = signature(update_method)
    if len(state_update_sig.parameters) != 1:
        raise AttributeError("plugin listener {} must have method 'state_update' with one parameter".format(listener))

    return listener
