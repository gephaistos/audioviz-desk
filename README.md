# audioviz

Simple [GTK](https://www.gtk.org/)-based Python library that implements audio spectrum visualization widget for desktop.

![Demo](/media/demo.gif)

## Installation

### Requirements

- Linux
- PulseAudio
- GTK+3

To install Python bindings for GTK (PyGObject) follow official [guide](https://pygobject.readthedocs.io/en/latest/getting_started.html).

For example, on Ubuntu, this should work fine to get all the dependencies for PyGObject:

```bash
apt install libgirepository1.0-dev gcc libcairo2-dev pkg-config python3-dev gir1.2-gtk-3.0
```

Finally, install audioviz with:

```bash
python3 -m pip install git+https://github.com/gephaistos/audioviz-desk
```

or clone the repo and in project's folder run:

```bash
python3 -m pip install .
```

## Usage

audioviz is installed in system as an application and has only cli so far.

Basically, to run audioviz with default parameters use command:

```bash
audioviz
```

To see available options run in terminal:

```bash
audioviz -h
```

### Configuration

All configurable parameters are set via configuration file.
Default configuration file is delivered within the package.
You can use/modify it directly or create a new one and pass it
on lauch:

```bash
audioviz -c path/to/my/config.cfg
```

All the parameters are described in the
[default file](https://github.com/gephaistos/audioviz-desk/tree/main/audioviz/cli/data/config.cfg).

Location of the default file can be obtained by:

```bash
audioviz -d
```

*Note:*

If visualizer does not appear (or is frozen) you might need to use a different source instead of the default.
Take a look at the `device` parameter in configuration file.

## Appearance example

![Showcase](/media/showcase.png)
