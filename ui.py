#!/usr/bin/python
# -*- coding: utf-8 -*-
#

import thread
import gtk
import gobject


def humanize_size(size):
    """
    Return the file size as a nice, readable string.
    """
    for limit, suffix in ((1024**3, 'GiB'), (1024**2, 'MiB'), (1024, 'KiB')):
        hsize = float(size) / limit
        if hsize > 0.5:
            return '%.2f %s' % (hsize, suffix)


def gtk_idle(func):
    """Call the given function as GTK idle function, NOT waiting for results"""

    def wrapper(*args, **kwargs):
        """
        Internal wrapper for gtk_idle.
        """

        def task():
            """
            Setting an event with current task.
            """
            func(*args, **kwargs)

        gobject.idle_add(task)

    wrapper.__name__ = func.__name__
    return wrapper


def threaded(func):
    """Call the given function in a new thread"""
    def wrapper(*args, **kwargs):
        """
        Internal wrapper for the threaded decorator.
        """
        thread.start_new_thread(func, args, kwargs)

    wrapper.__name__ = func.__name__
    return wrapper


class GladeWindow(object):

    callbacks = {}
    builder = None

    def __init__(self):
        '''
        Init GladeWindow, stores the objects's potential callbacks for later.
        You have to call connect_signals() when all descendants are ready.'''
        GladeWindow.callbacks.update(dict([[x, getattr(self, x)]
                                                        for x in dir(self)]))

    def __getattr__(self, attribute):
        '''Allow direct use of window's widgets.'''
        widget = GladeWindow.builder.get_object(attribute)
        if widget is None:
            raise AttributeError('Widget \'%s\' not found' % attribute)
        self.__dict__[attribute] = widget # cache result
        return widget

    @staticmethod
    def connect_signals():
        '''Connect all GladeWindow objects to theirs respective signals.'''
        GladeWindow.builder.connect_signals(GladeWindow.callbacks)


def append_column(treeview, name, renderer=gtk.CellRendererText,
                   renderer_properties=None, signals=None, column_mapping=None,
                   expand=False):
        """
        Append a new column to a treeview.
        """
        cellrenderer = renderer()
        if renderer_properties:
            for k in renderer_properties:
                cellrenderer.set_property(k, renderer_properties[k])
        if signals:
            for k in signals:
                cellrenderer.connect(k, *signals[k])
        column = gtk.TreeViewColumn(name, cellrenderer, **column_mapping)
        column.set_expand(expand)
        treeview.append_column(column)
