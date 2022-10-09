import argparse
import os
from importlib import resources

from audioviz.render import Renderer

from ..config import parse_config


def parse() -> str:
    parser = argparse.ArgumentParser()
    parser.add_argument('-c', '--config', type=str, required=False,
                        help='Path to configuration file. Default is in package data.')
    parser.add_argument('-s', '--sources', action='store_true',
                        help='List available devices and sources to listen to.')
    parser.add_argument('-d', '--default', action='store_true',
                        help='Show location of the default configuration file.')
    args = parser.parse_args()

    # default config
    config_path = resources.files(__package__).joinpath('data/config.cfg')
    if args.config:
        if not os.path.exists(args.config):
            print('Could not find {}! Using deafult configuration.'.format(args.config))
        else:
            config_path = args.config

    return config_path, args.sources, args.default


def list_sources():
    import pulsectl
    pulse = pulsectl.Pulse('sources-list')
    devices = pulse.source_list()
    apps = [source.proplist['application.name'] for source in pulse.sink_input_list()]

    return devices, apps


def run():
    config_path, show_sources, show_config_location = parse()

    if show_config_location:
        print('Configuration file in use: {}'.format(config_path))
        return

    if show_sources:
        devices, apps = list_sources()
        print('Available devices:')
        for device in devices:
            print(device.name)
        print('Available apps:')
        for app in apps:
            print(app)
        return

    config = parse_config(config_path)
    r = Renderer(config)
    r.start()
