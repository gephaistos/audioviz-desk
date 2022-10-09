import time

import gi
gi.require_version('Gtk', '3.0')
from gi.repository import GLib, Gtk, Gdk

import cairo
import numpy as np
import pulsectl

from .effect import monstercat
from .record import Recorder


class Renderer:
    def __init__(self, config: dict):
        self.recorder = Recorder(config)
        self.recorder.add_callback(self.transfer_data)
        self.pulse = None

        self.fps = config['fps']

        self.renderer_active = True
        self.listen_apps = config['apps']

        # bars
        self.bars_num = self.recorder.num_bands()
        self.bars_color = Gdk.RGBA(*config['color'])
        self.bars_padding = config['padding']
        self.right_offset = config['right_offset']
        self.bot_offset = config['bot_offset']
        self.left_offset = config['left_offset']
        self.top_offset = config['top_offset']

        self.rotation = config['rotation']

        # initial value and on pause
        self.mag_min = 0.01

        self.band_mags = np.full(self.recorder.num_bands(),
                                 self.mag_min, dtype=np.float64)

        # window
        self.window = Gtk.Window()
        self.window.set_type_hint(Gdk.WindowTypeHint.DESKTOP)
        screen = self.window.get_screen()
        mon_geom = screen.get_display().get_primary_monitor().get_geometry()
        screen_size = [mon_geom.width - mon_geom.x, mon_geom.height - mon_geom.y]
        if config['size'] != 'screensize':
            width, height = config['size']
            if width > screen_size[0]:
                print('Set width is larger than screen width, falling to screen width.')
                width = screen_size[0]
            if height > screen_size[1]:
                print('Set height is larger than screen height, falling to screen height.')
                height = screen_size[1]

            pos_x, pos_y = config['position']
            if pos_x + width > screen_size[0]:
                print('Set width position makes window fall beyond screen border. Repositioning')
                pos_x = screen_size[0] - width

            if pos_y + height > screen_size[1]:
                print('Set height position makes window fall beyond screen border. Repositioning')
                pos_y = screen_size[1] - height

            self.window.set_default_size(width, height)
            self.window.move(pos_x, pos_y)
        else:
            self.window.set_default_size(*screen_size)

        # set window transparent
        self.window.set_app_paintable(True)
        self.window.set_visual(screen.get_rgba_visual())
        self.window.connect("draw", self.transparent_bckg)

        # drawing widget
        self.draw_area = Gtk.DrawingArea()
        self.draw_area.connect("draw", self.render_bars)
        self.window.add(self.draw_area)

        if self.listen_apps:
            GLib.timeout_add(1000 / self.fps, self.on_update_with_source)
        else:
            GLib.timeout_add(1000 / self.fps, self.on_update)
        self.window.connect("check-resize", self.on_resize)
        self.window.connect("key-press-event", self.check_escape)
        self.window.connect("destroy", self.stop)

        # self.fps_monitor = time.time()

        self.window.show_all()

    def transparent_bckg(self, widget, cr):
        cr.set_source_rgba(1.0, 1.0, 1.0, 0.0)
        cr.set_operator(cairo.OPERATOR_SOURCE)
        cr.paint()

        return False

    def transfer_data(self):
        self.band_mags = self.recorder.band_mags

    def on_update(self):
        self.draw_area.queue_draw()
        return True

    def on_update_with_source(self):
        # increases CPU usage by 2% compared to simple `on_update`
        corked = True
        for source in self.pulse.sink_input_list():
            if source.proplist['application.name'] in self.listen_apps:
                corked &= source.corked

        if corked:
            if self.renderer_active:
                self.recorder.pause()
                time.sleep(0.1)
                self.band_mags.fill(self.mag_min)
                self.draw_area.queue_draw()
                self.renderer_active = False
        else:
            if not self.renderer_active:
                self.recorder.resume()
                self.renderer_active = True
            self.draw_area.queue_draw()

        return True

    def on_resize(self, *args):
        if self.rotation == 0:
            self.bars_start_pos = self.draw_area.get_allocated_height() - self.bot_offset
            self.bars_max_height = self.bars_start_pos - self.top_offset

            total_bars_width = (self.draw_area.get_allocated_width()
                                - self.right_offset - self.left_offset) \
                - self.bars_padding * (self.bars_num - 1)
            self.bar_width = max(int(total_bars_width / self.bars_num), 1)
        elif self.rotation == 90:
            self.bars_start_pos = self.draw_area.get_allocated_width() - self.right_offset
            self.bars_max_height = self.bars_start_pos - self.left_offset

            total_bars_width = (self.draw_area.get_allocated_height()
                                - self.bot_offset - self.top_offset) \
                - self.bars_padding * (self.bars_num - 1)
            self.bar_width = max(int(total_bars_width / self.bars_num), 1)
        elif self.rotation == 180:
            self.bars_start_pos = self.top_offset
            self.bars_max_height = self.draw_area.get_allocated_height() - self.bot_offset

            total_bars_width = (self.draw_area.get_allocated_width()
                                - self.right_offset - self.left_offset) \
                - self.bars_padding * (self.bars_num - 1)
            self.bar_width = max(int(total_bars_width / self.bars_num), 1)
        else:
            self.bars_start_pos = self.left_offset
            self.bars_max_height = self.draw_area.get_allocated_width() - self.right_offset

            total_bars_width = (self.draw_area.get_allocated_height()
                                - self.bot_offset - self.top_offset) \
                - self.bars_padding * (self.bars_num - 1)
            self.bar_width = max(int(total_bars_width / self.bars_num), 1)

    def render_bars(self, widget, cr):
        # delta = time.time() - self.fps_monitor
        # print('FPS:', 1 / delta)
        # self.fps_monitor = time.time()
        cr.set_source_rgba(*self.bars_color)

        heights = self.bars_max_height * self.band_mags
        monstercat(heights)

        if self.rotation == 0:
            dx = self.left_offset
            for height in heights:
                cr.rectangle(dx, self.bars_start_pos, self.bar_width, -height)
                dx += self.bar_width + self.bars_padding
        elif self.rotation == 90:
            dy = self.draw_area.get_allocated_height() - self.bot_offset
            for height in heights:
                cr.rectangle(self.bars_start_pos, dy, -height, -self.bar_width)
                dy -= self.bar_width + self.bars_padding
        elif self.rotation == 180:
            dx = self.draw_area.get_allocated_width() - self.right_offset
            for height in heights:
                cr.rectangle(dx, self.bars_start_pos, -self.bar_width, height)
                dx -= self.bar_width + self.bars_padding
        else:
            dy = self.top_offset
            for height in heights:
                cr.rectangle(self.bars_start_pos, dy, height, self.bar_width)
                dy += self.bar_width + self.bars_padding
        cr.fill()

    def start(self):
        self.recorder.connect()
        self.recorder.start()
        self.pulse = pulsectl.Pulse('source-checker')
        print('Press Esc to exit.')
        Gtk.main()

    def stop(self):
        self.recorder.stop()
        self.recorder.join()
        self.recorder.disconnect()
        self.pulse.close()
        Gtk.main_quit()

    def check_escape(self, widget, event):
        if event.keyval == Gdk.KEY_Escape:
            self.stop()
            return True
        return False
