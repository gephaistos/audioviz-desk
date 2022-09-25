import time

import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, Gdk, GLib
import cairo
import numpy as np

from .record import Recorder


class Renderer:
    def __init__(self):
        self.recorder = Recorder()
        self.recorder.add_callback(self.transfer_data)

        self.bars_padding = 5
        self.bars_num = self.recorder.num_bands()
        self.right_offset = 5
        self.bottom_offset = 5
        self.left_offset = 5
        self.top_offset = 5

        hex_color = '#3F5F50C0'.lstrip("#")
        nums = [int(hex_color[i:i + 2], 16) / 255.0 for i in range(0, 7, 2)]
        self.bars_color = Gdk.RGBA(*nums)
        self.mag_min = -75 # goes up to -145
        self.mag_max = 0
        self.band_mags = np.full(self.recorder.num_bands(),
                                 self.mag_min, dtype=np.float64)

        # window
        self.window = Gtk.Window()
        screen = self.window.get_screen()
        mon_geom = screen.get_display().get_primary_monitor().get_geometry()
        screen_size = [mon_geom.width - mon_geom.x, mon_geom.height - mon_geom.y]

        self.window.set_type_hint(Gdk.WindowTypeHint.DESKTOP)
        self.window.set_default_size(*screen_size)

        # set window transparent
        self.window.set_app_paintable(True)
        self.window.set_visual(screen.get_rgba_visual())
        self.window.connect("draw", self.transparent_bckg)

        # drawing widget
        self.draw_area = Gtk.DrawingArea()
        self.draw_area.connect("draw", self.render_bars)
        self.window.add(self.draw_area)

        desired_fps = 60
        GLib.timeout_add(1000 / desired_fps, self.on_update)
        self.window.connect("check-resize", self.on_resize)
        self.window.connect("key-press-event", self.check_escape)
        self.window.connect("destroy", self.stop)

        self.fps_monitor = time.time()

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

    def on_resize(self, *args):
        self.bars_win_width = self.draw_area.get_allocated_width() - self.right_offset
        self.bars_win_height = self.draw_area.get_allocated_height() - self.bottom_offset

        total_width = (self.bars_win_width - self.left_offset
                        ) - self.bars_padding * (self.bars_num - 1)
        self.bars_width = max(int(total_width / self.bars_num), 1)
        self.bars_height = self.bars_win_height - self.top_offset
        self.bars_height /= 2

    def render_bars(self, widget, cr):
        # delta = time.time() - self.fps_monitor
        # print('FPS:', 1 / delta)
        # self.fps_monitor = time.time()
        cr.set_source_rgba(*self.bars_color)

        norm_heights = np.clip( # normalize
            (self.band_mags - self.mag_min) / (self.mag_max - self.mag_min),
            0.001, 1.0
        )
        heights = self.bars_height * norm_heights

        dx = self.left_offset
        for height in heights:
            cr.rectangle(dx, self.bars_win_height, self.bars_width, -height)
            dx += self.bars_width + self.bars_padding
        cr.fill()

    def start(self):
        self.recorder.start()
        print('Press Esc to close.')
        Gtk.main()

    def stop(self):
        self.recorder.stop()
        self.recorder.join()
        Gtk.main_quit()

    def check_escape(self, widget, event):
        if event.keyval == Gdk.KEY_Escape:
            self.stop()
            return True
        return False

