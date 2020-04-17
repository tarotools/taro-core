import pytest

from taro import plugin
from test import plugins, Listener
from test.plugins import invalid_listener, none_listener


def test_load_no_listener():
    with pytest.raises(AttributeError):
        plugin.load_plugin(plugins)  # plugins module doesn't have create_listener method


def test_load_none_listener():
    with pytest.raises(ValueError):
        plugin.load_plugin(none_listener)  # create_listener returns None


def test_load_invalid_listener():
    with pytest.raises(AttributeError):
        plugin.load_plugin(invalid_listener)  # create_listener returns listener with invalid notify method


def test_plugin_discovered():
    plugins_ = plugin.discover_plugins('test', ['test'])
    assert len(plugins_) == 1
    assert isinstance(plugins_['test'], Listener)