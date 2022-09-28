import argparse
import os
from importlib import resources

from audioviz.render import Renderer
from ..config import parse_config


def parse() -> str:
    parser = argparse.ArgumentParser()
    parser.add_argument('-c', '--config', type=str, required=False,
                        help='Path to configuration file. Default is in package data.')
    args = parser.parse_args()

    # default config
    config_path = resources.files(__package__).joinpath('data/config.cfg')
    if args.config:
        if not os.path.exists(args.config):
            print('Could not find {}! Using deafult configuration.'.format(args.config))
        else:
            config_path = args.config

    return config_path


def run():
    config_path = parse()
    config = parse_config(config_path)
    r = Renderer(config)
    r.start()