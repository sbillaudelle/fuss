#! /usr/bin/env python
# -*- coding: utf-8 -*-

# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston,
# MA 02110-1301, USA.

import os
import time
import gobject
import gtk
import clutter
import cluttergtk
import cairo
import pango
import pangocairo

import ooxcb
from ooxcb.protocol import xproto, screensaver, composite

import cream
import cream.gui

import fuss.helper

class XScreenSaverSession(object):

    """ Wrapper for the XScreenSaverSession. """

    def __init__(self):

        self.connection = ooxcb.connect()

        self.root = self.connection.setup.roots[self.connection.pref_screen].root

    def query(self):
        """
        Get the time since the last mouse movement.

        :returns: Time since last mouse/keyboard activity.
        :rtype: `int`
        """
        reply = screensaver.DrawableMixin.query_info(self.root).reply()
        return reply.state, int(round(float(reply.ms_until_server) / 1000, 1)), int(round(float(reply.ms_since_user_input) / 1000, 1))


class Text(clutter.CairoTexture):

    def __init__(self, text, blur=False, font=None):

        self.text = text
        self.blur = blur
        self.font = font or pango.FontDescription('Sans 12')

        self.width, self.height = [i + 6 for i in fuss.helper.get_text_preferred_size(self.text, font=self.font)]

        clutter.CairoTexture.__init__(self, int(self.width), int(self.height))

        self.render()


    def set_text(self, text):

        self.text = text
        self.width, self.height = [i + 6 for i in fuss.helper.get_text_preferred_size(self.text, font=self.font)]
        self.set_surface_size(self.width, self.height)
        self.set_size(self.width, self.height)

        self.render()


    def get_text(self):
        return self.text


    def render(self):

        self.clear()

        surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, int(self.width), int(self.height))
        ctx = cairo.Context(surface)
        ctx.move_to(3, 3)

        ctx.set_source_rgb(0, 0, 0)
        pango_ctx = pangocairo.CairoContext(ctx)
        layout = pango_ctx.create_layout()
        layout.set_width(int((self.width - 6) * pango.SCALE))
        layout.set_alignment(pango.ALIGN_CENTER)
        layout.set_font_description(self.font)
        layout.set_markup(self.text)
        
        pango_ctx.show_layout(layout)

        if self.blur:
            surface = fuss.helper.blur(surface, 5)
            ctx = cairo.Context(surface)
            ctx.move_to(3, 3)

            ctx.set_source_rgb(1, 1, 1)
            pango_ctx = pangocairo.CairoContext(ctx)
            layout = pango_ctx.create_layout()
            layout.set_width(int((self.width - 6) * pango.SCALE))
            layout.set_alignment(pango.ALIGN_CENTER)
            layout.set_font_description(self.font)
            layout.set_markup(self.text)
            
            pango_ctx.show_layout(layout)

        ctx = self.cairo_create()
        ctx.set_source_surface(surface)
        ctx.paint()


class Fuss(cream.Module):

    visible = False

    def __init__(self):

        cream.Module.__init__(self, 'org.sbillaudelle.Fuss')

        self.screensaver = XScreenSaverSession()

        self.window = gtk.Window()
        self.window.fullscreen()

        self.window.set_opacity(0)

        self.display = self.window.get_display()
        self.screen = self.display.get_default_screen()
        self.width, self.height = self.screen.get_width(), self.screen.get_height()
        self.window.resize(self.width, self.height)
        self.window.set_property('skip-pager-hint', True)
        self.window.set_property('skip-taskbar-hint', True)
        self.window.set_property('accept-focus', False)
        self.window.stick()
        self.window.set_keep_above(True)

        self.embed = cluttergtk.Embed()
        self.window.add(self.embed)

        self.embed.realize()
        self.stage = self.embed.get_stage()
        self.stage.set_color(clutter.Color(50, 50, 50))

        self.background = clutter.texture_new_from_file(os.path.expanduser(self.config.background_image))
        self.stage.add(self.background)


        # Display the time...
        self.time = Text('10:15', blur=True, font=pango.FontDescription('Droid Sans 220'))
        self.time.set_position((self.width - self.time.get_width()) / 2, 400)

        self.time.connect('allocation-changed', self.time_allocation_changed_cb)

        self.stage.add(self.time)


        # Display the date...
        self.date = Text('Montag, 6. Dezember 2010', blur=True, font=pango.FontDescription('Droid Sans 36'))
        self.date.set_position((self.width - self.date.get_width()) / 2, 700)

        self.date.connect('allocation-changed', self.date_allocation_changed_cb)

        self.stage.add(self.date)

        self.window.show_all()
        
        self.window.window.input_shape_combine_region(gtk.gdk.Region(), 0, 0)

        pixmap = gtk.gdk.Pixmap(None, 1, 1, 1)
        color = gtk.gdk.Color()
        cursor = gtk.gdk.Cursor(pixmap, pixmap, color, color, 0, 0)

        self.window.window.set_cursor(cursor)

        self.update()
        gobject.timeout_add(333, self.update)
        
        self.connection = ooxcb.connect()
        self.root = self.connection.setup.roots[self.connection.pref_screen].root

        self.cow = gtk.gdk.window_foreign_new(composite.WindowMixin.get_overlay_window(self.root).reply().overlay_win.xid)
        self.window.window.redirect_to_drawable(self.cow, 0, 0, 0, 0, self.window.get_allocation().width, self.window.get_allocation().height)
        
        
    def quit(self):

        composite.WindowMixin.release_overlay_window(self.root)
        cream.Module.quit(self)


    def fade_in(self):

        def fade(timeline, status):
            self.window.set_opacity(status)

        self.visible = True
        self.messages.debug("Fading in...")

        self.window.window.input_shape_combine_region(gtk.gdk.region_rectangle((0, 0, 1440, 900)), 0, 0)

        t = cream.gui.Timeline(1000, cream.gui.CURVE_SINE)
        t.connect('update', fade)
        t.run()


    def fade_out(self):

        def fade(timeline, status):
            self.window.set_opacity(1 - status)

        self.visible = False
        self.window.window.input_shape_combine_region(gtk.gdk.Region(), 0, 0)
        self.messages.debug("Fading out...")

        t = cream.gui.Timeline(1000, cream.gui.CURVE_SINE)
        t.connect('update', fade)
        t.run()


    def update(self):

        t = time.strftime('%H:%M')

        if self.time.get_text() != t:
            self.time.set_text(t)

        d = time.strftime('%A, %d. %B %Y')

        if self.date.get_text() != d:
            self.date.set_text(d)

        screensaver_info = self.screensaver.query()
        self.messages.debug("'{0}' seconds left until fading in...".format(screensaver_info[1]))

        if screensaver_info[0] == 1 and not self.visible:
            self.fade_in()
        elif screensaver_info[0] == 0 and self.visible:
            self.fade_out()

        return True


    def time_allocation_changed_cb(self, *args):
        self.time.set_position((self.width - self.time.get_width()) / 2, 400)

    def date_allocation_changed_cb(self, *args):
        self.date.set_position((self.width - self.date.get_width()) / 2, 700)


if __name__ == '__main__':
    Fuss().main()
