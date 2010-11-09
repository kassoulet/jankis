#!/usr/bin/python
# -*- coding: utf-8 -*-
#

"""
Jankis Duplicate Finder
© 2010 Gautier Portet - <kassoulet gmail com>
"""

NAME = 'Jankis Duplicate Finder'
VERSION = '0.1'
CONFIG_FILE = 'jankis.conf'

print '%s (%s)' % (NAME, VERSION)

import os
import sys
import time
from optparse import OptionParser

import finder
from finder import walk, scan, current_file

quiet = False


def expand_size_suffix(size):
    """
    Convert a string containing a size to an int.
    Recognize size suffixes eg. 62 15k 47M 92G.
    """
    intsize = int(''.join(s for s in size if s.isdigit()))
    suffix = size[-1].lower()
    try:
        multiplier = 1024 ** (dict(k=1,m=2,g=3)[suffix])
    except KeyError:
        multiplier = 1
    return intsize * multiplier 


def humanize_size(size):
    """
    Return the file size as a nice, readable string.
    """
    for limit, suffix in ((1024**3, 'G'), (1024**2, 'M'), (1024, 'K')):
        hsize = float(size) / limit
        if hsize > 0.5:
            return '%.1f%s' % (hsize, suffix)


next_progress = 0
def added_file(filename):
    """Called when a file is added in matcher."""
    global next_progress
    if not quiet:
        t = (time.time() * 10)
        if t < next_progress:
            return
        c = ['-','\\','|','/'][int(t)%4]
        sys.stdout.write('Scanning... %s\r' % c)
        sys.stdout.flush()
        next_progress = t + 1


def scanned_file(scanned, to_scan, match=None):
    """Called when a file is hashed by matcher."""
    global next_progress
    if not quiet:
        t = (time.time() * 10)
        if t < next_progress:
            return
        sys.stdout.write('Scanning... %d/%d\r' % (scanned, to_scan))
        sys.stdout.flush()
        next_progress = t + 1


def print_matches(matches):
    """Print the final result list."""
    for i, group in enumerate(matches):
        print '\nGroup #%d' % i
        for match in group:
            filename, size, md5 = match
            size = humanize_size(size)
            print '%7s %s %s' % (size, md5[:6], filename)


def tui_main(*args):

    # parse arguments
    usage = "usage: %prog [options] folder"
    parser = OptionParser(usage=usage)
    parser.add_option("-s", "--minimal-size", dest="minsize", default='1M',
                      help="Minimal size. (You can use size suffixes"
                      " eg. 62 15k 47M 92G).")
    parser.add_option("-L", "--follow-links",
                      dest="follow_links", 
                      action="store_true",
                      help="Follow symbolinc links.")
    parser.add_option("-q", "--quiet",
                      dest="quiet", 
                      action="store_true",
                      help="Do not display progress info.")

    (options, args) = parser.parse_args()
    if len(args) != 1:
        parser.error("incorrect number of arguments")    
        
    folder = args[0]
    minimal_size = expand_size_suffix(options.minsize)
    follow_links = options.follow_links
    quiet = options.quiet

    # scan folder
    start = time.time()
    matches = scan(folder, minimal_size, follow_links,
        add_file_callback=added_file,
        add_match_callback=scanned_file,
    )
    duration = time.time()-start
    if not quiet:
        print
        print 'Found %d matche(s) in %.3fs' % (len(matches), duration)
    print_matches(matches)


try:
    from jankis_gtk import gui_main as main
except ImportError:
    main = tui_main
    
main(NAME, VERSION, 'ui.glade')


