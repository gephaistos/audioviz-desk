"""Module contains fucntions to process configuration step of visualizer.
"""


from configparser import ConfigParser
from difflib import get_close_matches


def parse_config(config_path: str) -> dict[str, bool|int|str|tuple|list]:
    parser = ConfigParser()
    parser.read(config_path)
    validate_sections_and_options(parser)

    config = {}

    config['fps'] = validate_fps(parser.getint('Window', 'fps'))
    config['size'] = validate_size(parser.get('Window', 'size'))
    config['position'] = validate_position(parser.get('Window', 'position'))
    if config['size'] == 'screensize' and config['position'] != (0, 0):
        print('Size was set to screensize but position is not 0, 0')
        print('Position is forced to be 0, 0')

    config['device'] = parser.get('Listen', 'device')
    #config['apps'] = validate_apps(parser.get('Listen', 'apps'))

    config['color'] = validate_color(parser.get('Bars', 'color'))
    config['padding'] = parser.getint('Bars', 'padding')
    config['right_offset'] = parser.getint('Bars', 'right_offset')
    config['bot_offset'] = parser.getint('Bars', 'bot_offset')
    config['left_offset'] = parser.getint('Bars', 'left_offset')
    config['top_offset'] = parser.getint('Bars', 'top_offset')
    config['bands_distr'] = validate_distr(parser.get('Bars', 'distr'))

    #config['rotation'] = validate_rotation(parser.getint('Effect', 'rotation'))

    config['frequency'] = validate_frequency(parser.getint('Spectrum', 'frequency'))
    config['channels'] = validate_channels(parser.getint('Spectrum', 'channels'))
    config['window_type'] = validate_window(parser.get('Spectrum', 'window'))
    config['weighting_type'] = validate_weighting(parser.get('Spectrum', 'weighting'))
    config['scaling_type'] = validate_scaling(parser.get('Spectrum', 'scaling'))

    config['frame_size'] = 8192  # discouraged to be set by user
    config['buffer_size'] = 512  # discouraged to be set by user

    return config


def validate_sections_and_options(parser: ConfigParser):
    valid_secitons = ['Window', 'Listen', 'Bars', 'Effect', 'Spectrum']
    valid_options = [
        'fps', 'size', 'position',
        'device', 'apps',
        'color', 'padding', 'right_offset', 'bot_offset', 'left_offset', 'top_offset', 'distr',
        'rotation',
        'frequency', 'channels', 'window', 'weighting', 'scaling'
    ]

    invalid_section_suggestions = []
    invalid_option_suggestions = []
    for section in parser.sections():
        if section not in valid_secitons:
            invalid_section_suggestions.append((
                section,
                get_close_matches(section, valid_secitons, 1)[0]
            ))
        for option in parser.options(section):
            if option not in valid_options:
                invalid_option_suggestions.append((
                    option,
                    get_close_matches(option, valid_options, 1)[0]
                ))

    if invalid_section_suggestions or invalid_option_suggestions:
        for invalid_section, suggestion in invalid_section_suggestions:
            print('Invalid section {}. Did you mean {}?'.format(invalid_section, suggestion))
        for invalid_option, suggestion in invalid_option_suggestions:
            print('Invalid option {}. Did you mean {}?'.format(invalid_option, suggestion))
        raise ValueError('Configuration error.')


def validate_fps(fps: int) -> int:
    if fps < 0:
        raise ValueError('Trying to go back in time, huh?'
                         'Wrong value for `fps` parameter. '
                         'Value cannot be negative.')
    if fps == 0:
        raise ValueError('Trying to stop the time, huh?'
                         'Wrong value for `fps` parameter. '
                         'Value cannot be zero.')
    if fps > 240:
            raise ValueError('FPS is too large. '
                             'Consider using value in range 1..240.')

    return fps


def validate_size(size: str) -> str|tuple[int, int]:
    if size == 'screensize':
        return size

    size = [int(val) for val in size.split(',')]

    if len(size) != 2:
        raise ValueError('Wrong value for `size` parameter. '
                         'It should contain two integers.')
    if any([val <= 0 for val in size]):
        raise ValueError('Wrong value for `size` parameter. '
                         'Values cannot be negative or zero.')

    return tuple(size)


def validate_position(position: str) -> tuple[int, int]:
    position = [int(val) for val in position.split(',')]

    if len(position) != 2:
        raise ValueError('Wrong value for `position` parameter. '
                         'It should contain two integers.')
    if any([val < 0 for val in position]):
        raise ValueError('Wrong value for `position` parameter. '
                         'Values cannot be negative.')

    return tuple(position)


def validate_apps(apps: str) -> list[str]:
    if apps == 'any':
        return []

    return [val.strip() for val in apps.split(',')]


def validate_color(color: str) -> tuple[int, int, int, int]:
    if len(color) != 8:
        raise ValueError('Wrong value for `color` parameter. '
                         'It should contain 8 hex digits.')

    values = [int(color[i:i + 2], 16) / 255.0 for i in range(0, 7, 2)]

    return tuple(values)


def validate_distr(distr: str) -> tuple[str, int]:
    distr = distr.split(',')
    if len(distr) != 2:
        raise ValueError('Wrong values for `distr` parameter.'
                         'It should contain 2 comma-separated values.')

    distr[1] = int(distr[1])
    if distr[0] == 'octave':
        if distr[1] > 12:
            raise ValueError('Fraction value for octave is too large. '
                             'Consider using value in range 1..12 (1-octave..1/12-octave).')
        if distr[1] < 1:
            raise ValueError('Fraction value for octave is too low. '
                             'Consider using value in range 1..12 (1-octave..1/12-octave).')
    elif distr[0] == 'uniform':
        if distr[1] > 128:
            raise ValueError('Bars number value for uniform is too large. '
                             'Consider using value in range 1..128.')
        if distr[1] < 1:
            raise ValueError('Bars number value for uniform is too low. '
                             'Consider using value in range 1..128.')
    else:
        raise ValueError('Wrong value for `distr` parameter. '
                         'Valid options: octave, uniform.')

    return tuple(distr)


def validate_rotation(rotation: int) -> int:
    if rotation not in [90, 180, 270]:
        raise ValueError('Wrong value for `rotatation` parameter. '
                         'Valid options: 90, 180, 270.')

    return rotation


def validate_frequency(frequency: int) -> int:
    if frequency < 0:
        raise ValueError('Wrong value for `frequency` parameter. '
                         'Value cannot be negative.')
    if frequency > 22579200:
            raise ValueError('Sampling frequency is too large. '
                             'Consider using value in range 8000..22579200.')
    if frequency < 8000:
        raise ValueError('Sampling frequency is too low. '
                         'Consider using value in range 8000..22579200.')

    return frequency


def validate_channels(channels: int) -> int:
    if channels != 1:
        raise ValueError('Only value 1 for `channels` parameter is currently supported.')

    return channels


def validate_window(window_type: str) -> str:
    if window_type not in ['hanning', 'rectangle']:
        raise ValueError('Wrong value for `window` parameter. '
                         'Valid options: hanning, rectangle.')

    return window_type


def validate_weighting(weighting_type: str) -> str:
    if weighting_type not in ['A', 'C', 'Z']:
        raise ValueError('Wrong value for `weighting` parameter. '
                         'Valid options: A, C, Z.')

    return weighting_type


def validate_scaling(scaling_type: str) -> str:
    if scaling_type not in ['log', 'lin']:
        raise ValueError('Wrong value for `scaling` parameter. '
                         'Valid options: log, lin.')

    return scaling_type