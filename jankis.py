#!/usr/bin/python
# -*- coding: utf-8 -*-
#

"""
Jankis Duplicate Finder
© 2010 Gautier Portet - <kassoulet gmail com>
"""

NAME = 'Jankis Duplicate Finder'
VERSION = 'proto'
CONFIG_FILE = 'jankis.conf'

import os
import time

import gtk
import gobject
gobject.threads_init()
import pango

import finder
from finder import walk, scan, current_file, abort
from ui import GladeWindow, threaded, humanize_size, append_column


class MatchList(object):
    """
    Manage the list of matches.
    """
    HUMAN_FILENAME, FILENAME, HUMAN_SIZE, SIZE, MD5, ORIGINAL, DELETE, DELETABLE, LINK, LINKABLE, VISIBLE, MATCH_ID = range(12)

    def __init__(self, treeview):
        """
        Create the model and prepare the treeview.
        """
        self.treeview = treeview

        self.liststore = apply(gtk.ListStore, [
              gobject.TYPE_STRING,    # human filename
              gobject.TYPE_STRING,    # filename
              gobject.TYPE_STRING,    # human size
              gobject.TYPE_INT,       # size
              gobject.TYPE_STRING,    # md5
              gobject.TYPE_BOOLEAN,   # original
              gobject.TYPE_BOOLEAN,   # delete
              gobject.TYPE_BOOLEAN,   # deletable
              gobject.TYPE_BOOLEAN,   # link
              gobject.TYPE_BOOLEAN,   # linkable
              gobject.TYPE_BOOLEAN,   # visible
              gobject.TYPE_INT,       # match id
        ])
        append_column(self.treeview, 'Keep', gtk.CellRendererToggle,
            renderer_properties=dict(activatable=True, radio=True),
            signals=dict(toggled=[self.on_original_toggled, self.liststore, self.ORIGINAL]),
            column_mapping=dict(active=self.ORIGINAL, visible=self.VISIBLE))

        append_column(self.treeview, 'Delete', gtk.CellRendererToggle,
            renderer_properties=dict(activatable=True),
            signals=dict(toggled=[self.on_delete_toggled, self.liststore, self.DELETE]),
            column_mapping=dict(active=self.DELETE, visible=self.VISIBLE, sensitive=self.DELETABLE))

        append_column(self.treeview, 'Link', gtk.CellRendererToggle,
            renderer_properties=dict(activatable=True),
            signals=dict(toggled=[self.on_link_toggled, self.liststore, self.LINK]),
            column_mapping=dict(active=self.LINK, visible=self.VISIBLE, sensitive=self.LINKABLE))

        append_column(self.treeview, 'Filename',
            renderer_properties=dict(ellipsize=pango.ELLIPSIZE_MIDDLE),
            column_mapping=dict(markup=self.HUMAN_FILENAME), expand=True)

        append_column(self.treeview, 'Size',
            column_mapping=dict(markup=self.HUMAN_SIZE))

        append_column(self.treeview, 'Hash',
            column_mapping=dict(markup=self.MD5))

        self.treeview.set_model(self.liststore)
        self.clear()

    def clear(self):
        """
        Remove all matches.
        """
        self.liststore.clear()
        self.nb_matches = 0

    def add(self, match):
        """
        Add a new match.
        """
        size = 0
        for duplicate in match:
            size += duplicate[1]

        self.liststore.append(['<i>Group %d</i>' % (self.nb_matches + 1), '',
                    '<b>%s</b>' % humanize_size(size),
                    size,
                    '', False, False, False, False, False, False, -1])
        for i, duplicate in enumerate(match):
            filename, size, md5 = duplicate
            path, filename = os.path.split(filename)
            self.liststore.append(['<small>%s</small>/%s' % (path, filename),
                    '%s/%s' % (path, filename),
                    '%s' % humanize_size(size),
                    size,
                    md5[:6],
                    True if i == 0 else False, False, True, False, True, True, self.nb_matches])
        self.nb_matches += 1
        self.validate_model()

    def validate_model(self):
        """
        Check the model and desactivate impossible or dangerous actions.
        TODO: only validate when inserting matches. Also, indicate links and
              partial matches.
        """
        matches = {}
        for i, item in enumerate(self.liststore):
            if item[self.ORIGINAL]:
                k = item[self.MATCH_ID]
                matches[k] = item

        for item in self.liststore:
            if item[self.ORIGINAL]:
                item[self.DELETE] = False
                item[self.LINK] = False
                item[self.DELETABLE] = False
                item[self.LINKABLE] = False
            else:
                item[self.DELETABLE] = True
                item[self.LINKABLE] = True

            if item[self.MATCH_ID] >= 0:
                original_md5 = matches[item[self.MATCH_ID]][self.MD5]
                if item[self.MD5] != original_md5:
                    item[self.LINKABLE] = False
                original = matches[item[self.MATCH_ID]][self.FILENAME]
                if os.path.samefile(original, item[self.FILENAME]):
                    item[self.LINKABLE] = False

    @property
    def items(self):
        """
        items getter
        """
        matches = {}
        for i, item in enumerate(self.liststore):
            if item[self.ORIGINAL]:
                k = item[self.MATCH_ID]
                matches[k] = item

        to_delete = []
        to_link = []
        to_delete_size = 0
        to_link_size = 0
        for item in self.liststore:
            if item[MatchList.DELETE]:
                to_delete.append(item[MatchList.FILENAME])
                to_delete_size += item[MatchList.SIZE]
            if item[MatchList.LINK]:
                to_link.append([item[MatchList.FILENAME], matches[item[MatchList.MATCH_ID]][self.FILENAME]])
                to_link_size += item[MatchList.SIZE]
        return to_delete, to_link, to_delete_size, to_link_size

    def on_original_toggled(self, cell, path, model, col_num):
        """
        Original checkbox clicked.
        """
        match_id = model[path][self.MATCH_ID]
        for item in model:
            if item[self.MATCH_ID] == match_id:
                item[self.ORIGINAL] = False

        iter = model.get_iter(path)
        model.set_value(iter, col_num, not cell.get_active())

        self.validate_model()
        self.changed()

    def on_delete_toggled(self, cell, path, model, col_num):
        """
        Delete checkbox clicked.
        """
        if not model[path][self.ORIGINAL] and model[path][self.DELETABLE]:
            iter = model.get_iter(path)
            model.set_value(iter, col_num, not cell.get_active())
            self.changed()

    def on_link_toggled(self, cell, path, model, col_num):
        """
        Link checkbox clicked.
        """
        if not model[path][self.ORIGINAL] and model[path][self.LINKABLE]:
            iter = model.get_iter(path)
            model.set_value(iter, col_num, not cell.get_active())
            self.changed()


def load_conf(obj):
    """
    Load configuration object from disk.
    """
    defaults = {
        'min_file_size': 10,
        'file_size_multiplier': 2,
        'follow_links': True,
    }
    conf = dict(defaults)
    try:
        content = open(CONFIG_FILE).read()
        conf.update(eval(content))
    except:
        pass

    for i in conf:
        setattr(obj, i, conf[i])


def save_conf(obj):
    """
    Save configuration object to disk.
    """
    items = ['min_file_size', 'file_size_multiplier', 'follow_links']
    conf = {}
    for i in items:
        conf[i] = getattr(obj, i)
    open(CONFIG_FILE, 'w').write(repr(conf))


class JankisWindow(GladeWindow):
    """Main application Window."""

    def __init__(self):
        """
        Create window.
        """
        GladeWindow.__init__(self)

        self.matchlist = MatchList(self.treeview_filelist)
        self.matchlist.changed = self.user_action

        self.mainwindow.show()
        self.scanning = False
        self.files_scanned = 0
        self.files_to_scan = None

        cell = gtk.CellRendererText()
        self.combobox_file_size_multiplier.pack_start(cell, True)
        self.combobox_file_size_multiplier.add_attribute(cell, 'text', 0)

        load_conf(self)

    def clear(self):
        """
        Clear the list.
        """
        self.matchlist.clear()

    def on_button_scan_home_clicked(self, *args):
        """
        Scan home folder.
        """
        self.scan(os.path.expanduser('~'))

    def on_button_scan_filesystem_clicked(self, *args):
        """
        Scan whole filesystem.
        """
        self.scan('/')

    def on_button_scan_folder_clicked(self, *args):
        """
        Display a folder chooser dialog, and scan it.
        """
        response = self.folderchooserdialog.run()
        self.folderchooserdialog.hide()
        if response:
            for folder in self.folderchooserdialog.get_filenames():
                self.scan(folder)

    def on_button_apply_clicked(self, *args):
        """
        Apply change list.
        """
        self.apply_changes(*self.matchlist.items)

    @threaded
    def apply_changes(self, deletes, links, deletes_size, links_size):
        self.mainwindow.set_sensitive(False)
        self.status('Enlarging your free disk space...')
        todo = len(deletes) + len(links)
        done = 0.0
        from time import sleep
        for f in deletes:
            print('delete: %s' % f)
            done += 1
            self.progressbar.set_fraction(done/todo)
        for d,s in links:
            print('link: %s -> %s' % (s,d))
            tmp = d+'-todelete'
            os.rename(d,tmp)
            os.link(s,d)
            os.remove(tmp)
            done += 1
            self.progressbar.set_fraction(done/todo)
        self.progressbar.set_fraction(0)
        self.status('%d delete(s), %d link(s), freed %s' % (len(deletes), len(links), humanize_size(deletes_size + links_size)))
        self.mainwindow.set_sensitive(True)
        self.apply_frame.hide()

    def sensitive(self):
        widgets = 'button_scan_home button_scan_filesystem button_scan_folder menubar'.split()
        for w in widgets:
            getattr(self, w,).set_sensitive(not self.scanning)
        self.button_stop.set_sensitive(self.scanning)

    def scan(self, folder):
        """
        Start a scan in given folder.
        """
        self.clear()
        self.scanning = True
        gobject.timeout_add(100, self.update_progress)
        minsize = self.get_file_size()
        self.scan_folder(folder, minsize, self.follow_links)

    def add_file(self, filename):
        """
        A file matching criteria was just found while walking.
        """
        self.files_scanned += 1

    def scanned_file(self, scanned, to_scan, match=None):
        """
        A new duplicate file was just found.
        match contains the info about all duplicates of a group.
        """
        self.status('Checking matches...')
        self.files_scanned = scanned
        self.files_to_scan = to_scan
        if match:
            self.matchlist.add(match)

    def user_action(self):
        """
        Update pending actions stats.
        """
        to_delete, to_link, to_delete_size, to_link_size = self.matchlist.items
        label = []
        if to_delete:
            label.append('<b>%d</b> file(s) to delete <i>(%s)</i>' % (len(to_delete), humanize_size(to_delete_size)))
        if to_link:
            label.append('<b>%d</b> file(s) to hardlink <i>(%s)</i>' % (len(to_link), humanize_size(to_link_size)))
        if label:
            self.label_apply.set_markup('\n'.join(label))
            self.apply_frame.show()
        else:
            self.apply_frame.hide()

    @threaded
    def scan_folder(self, folder, minimal_size=0, follow_links=False):
        """
        Actually do the scanning, in another thread.
        """
        finder.abort = False
        self.sensitive()
        self.status('Walking...')
        start = time.time()
        files = walk(folder, minimal_size, follow_links)
        self.files_scanned = 0
        self.files_to_scan = len(list(files))
        print('walked in %.3ss' % (time.time()-start))
        self.status('Scanning...')
        start = time.time()
        matches = scan(folder, minimal_size, follow_links,
            add_file_callback=self.add_file,
            add_match_callback=self.scanned_file,
        )
        if finder.abort:
            print('scanning stopped')
            self.status('Cancelled')
        else:
            duration = time.time()-start
            print('scanned in %.3fs' % duration)
            self.status('Found %d matche(s) in %.3fs' % (len(matches), duration))
        self.scanning = False
        self.sensitive()

    def get_file_size(self):
        """
        Get the selected minimal file size based on number and multiplier.
        """
        return self.min_file_size * [2**(10*x)for x in (0,1,2,3,4)] [self.file_size_multiplier]

    def update_progress(self):
        """
        Called during the scanning, take care of keeping the user informed.
        """
        if not self.scanning:
            self.progressbar.set_text('')
            self.progressbar.set_fraction(0)
            return False
        if self.files_scanned and (self.files_scanned != self.files_to_scan):
            self.progressbar.set_fraction(float(self.files_scanned) / self.files_to_scan)
            self.progressbar.set_text('%d/%d' % (self.files_scanned, self.files_to_scan))
        else:
            self.progressbar.pulse()
            if current_file:
                self.progressbar.set_ellipsize(pango.ELLIPSIZE_START)
                self.progressbar.set_text(current_file)
            else:
                self.progressbar.set_text('')

        return True

    def status(self, status=None):
        """
        Change or reset the status' text.
        """
        self.label_status.set_text(status if status else 'Ready')

    def on_menu_prefs_activate(self, *args):
        """
        Display the preferences dialog.
        """
        self.spinbutton_min_file_size.set_value(self.min_file_size)
        self.combobox_file_size_multiplier.set_active(self.file_size_multiplier)
        self.checkbutton_follow_links.set_active(self.follow_links)

        response = self.dialog_prefs.run()
        if response > 0:
            self.min_file_size = self.spinbutton_min_file_size.get_value_as_int()
            self.file_size_multiplier = self.combobox_file_size_multiplier.get_active()
            self.follow_links = self.checkbutton_follow_links.get_active()

            save_conf(self)

        self.dialog_prefs.hide()

    def on_button_stop_clicked(self, *args):
        """
        Abort the scan.
        """
        finder.abort = True

    def on_menu_about_activate(self, *args):
        """
        Display the about dialog.
        """

        self.aboutdialog.run()
        self.aboutdialog.hide()

    def on_mainwindow_delete_event(self, *args):
        """
        Quit.
        """
        gtk.main_quit()


def gui_main(name, version, gladefile):
    """
    Program entry point.
    """
    builder = gtk.Builder()
    builder.add_from_file(gladefile)
    GladeWindow.builder = builder

    window = JankisWindow()
    GladeWindow.connect_signals()

    #gobject.idle_add(win.filelist.add_uris, input_files) #TODO: args ?
    gtk.main()


gui_main(NAME, VERSION, 'ui.glade')
