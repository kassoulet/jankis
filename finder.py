#!/usr/bin/python
# -*- coding: utf-8 -*-
#

"""

"""

import os
import hashlib

from smartpath import _walk


# read one CHUNK_SIZE bytes to check duplicates.
CHUNK_SIZE = 1024

# buffer size when doing whole file md5.
BUFFER_SIZE = 64*1024

# this contains the currently processed file.
current_file = None
abort = False

def walk(root_folders, minimal_size=-1, follow_links=False,
            blacklist=None, whitelist=None):
    """
    Return an iterator with all files present in a list of files/folders
    """
    global current_file
    for folder in root_folders:
        #print 'walking:', folder
        for root, dirs, files in _walk(folder, follow_links=follow_links):
            #print root
            current_file = root
            for name in files:
                filename = os.path.join(root, name)
                try:
                    filesize = os.path.getsize(filename)
                except OSError: # invalids files, links, etc...
                    filesize = 0
                if filesize > minimal_size:
                    yield filename
                if abort:
                    return
    current_file = None


def get_file_hash(filename, limit_size=None, buffer_size=BUFFER_SIZE):
    """
    Return the md5 hash of given file as an hexadecimal string.
    limit_size can be used to read only the first n bytes of file.
    """
    # open file
    try:
        f = file(filename, "rb")
    except IOError:
        return 'NONE'

    # get md5 hasher
    hasher = hashlib.md5()

    if limit_size:
        # get the md5 of beginning of file
        chunk = f.read(limit_size)
        hasher.update(chunk)
    else:
        # get the md5 of whole file
        chunk = True
        while chunk:
            chunk = f.read(buffer_size)
            hasher.update(chunk)
            if abort:
                return 'ABORT'

    f.close()
    return hasher.hexdigest()


class DuplicateFinder:
    """
    """

    def __init__(self):
        """
        Create the DuplicateFinder object.
        """
        # duplicate matches
        self.hashlist = {}
        # number of files with same hash
        self.hashcount = {}
        self.totalsize = 0
        self.totalfiles = 0
        self.dupfiles = 0
        self.dupsize = 0

    def add_file(self, filename):
        """
        Compare the given file to our lists of hashes
        """
        # compute md5
        h = get_file_hash(filename, CHUNK_SIZE)

        # increase count
        count = self.hashcount.get(h, 0) + 1
        self.hashcount[h] = count

        # store md5 and filename for later use
        f = self.hashlist.get(h, [])
        f.append(filename)
        self.hashlist[h] = f

        # update stats
        self.totalfiles += 1
        self.totalsize += os.path.getsize(filename)

    def process(self, progress_listener=None, skip_md5=False):
        """
        Check for duplicates.
        """
        matches = []
        scanned = to_scan = 0
        for h, f in self.hashlist.iteritems():
            if self.hashcount[h] < 2:
                # present only one time, skip
                continue
            to_scan += len(f)

        for h, f in self.hashlist.iteritems():
            if abort:
                return
            if self.hashcount[h] < 2:
                # present only one time, skip
                continue

            # reference file
            refname = f[0]
            try:
                refsize = os.path.getsize(refname)
            except OSError:
                continue
            refmd5 = get_file_hash(refname) if not skip_md5 else 'skipped'
            #print '%10d   %s' % (refsize, refname)
            match = []
            match.append([refname, refsize, refmd5])
            scanned += 1
            if progress_listener:
                progress_listener(scanned, to_scan)

            for filename in f[1:]:
                # and its copies
                try:
                    size = os.path.getsize(filename)
                except OSError:
                    continue
                md5 = get_file_hash(filename) if not skip_md5 else 'skipped'

                match.append([filename, size, md5])

                status = ' '
                msg = ''
                if md5 != refmd5:
                    status = '!'
                    msg = ' partial match only!'

                #print '%10d %s %s%s' % (size, status, filename, msg), os.path.samefile(refname, filename)
                self.dupsize += size
                scanned += 1
                if progress_listener:
                    progress_listener(scanned, to_scan)

            self.dupfiles += 1
            matches.append(match)
            if progress_listener:
                progress_listener(scanned, to_scan, match)
            #print
        return matches


def scan(folders, minimal_size, follow_links,
        add_file_callback=None, add_match_callback=None):
    finder = DuplicateFinder()
    for f in walk(folders, minimal_size, follow_links):
        finder.add_file(f)
        if add_file_callback:
            add_file_callback(f)
    return finder.process(add_match_callback)
