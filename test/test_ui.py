# This file is part of beets.
# Copyright 2011, Adrian Sampson.
#
# Permission is hereby granted, free of charge, to any person obtaining
# a copy of this software and associated documentation files (the
# "Software"), to deal in the Software without restriction, including
# without limitation the rights to use, copy, modify, merge, publish,
# distribute, sublicense, and/or sell copies of the Software, and to
# permit persons to whom the Software is furnished to do so, subject to
# the following conditions:
# 
# The above copyright notice and this permission notice shall be
# included in all copies or substantial portions of the Software.

"""Tests for the command-line interface.
"""
import unittest
import os
import shutil
import textwrap
from StringIO import StringIO
import logging

import _common
from beets import library
from beets import ui
from beets.ui import commands
from beets import autotag
from beets import mediafile
from beets import importer

TEST_TITLES = ('The Opener','The Second Track','The Last Track')
class ImportTest(unittest.TestCase):
    def setUp(self):
        self.io = _common.DummyIO()
        #self.io.install()

        # Suppress logging output.
        log = logging.getLogger('beets')
        log.setLevel(logging.CRITICAL)

        self.libdb = os.path.join('rsrc', 'testlib.blb')
        self.lib = library.Library(self.libdb)
        self.libdir = os.path.join('rsrc', 'testlibdir')
        self.lib.directory = self.libdir
        self.lib.path_formats = {
            'default': os.path.join('$artist', '$album', '$title')
        }

        self.srcdir = os.path.join('rsrc', 'testsrcdir')

    def tearDown(self):
        self.io.restore()
        if os.path.exists(self.libdb):
            os.remove(self.libdb)
        if os.path.exists(self.libdir):
            shutil.rmtree(self.libdir)
        if os.path.exists(self.srcdir):
            shutil.rmtree(self.srcdir)

    def _create_test_file(self, filepath, metadata):
        """Creates an mp3 file at the given path within self.srcdir.
        filepath is given as an array of folder names, ending with the
        file name. Sets the file's metadata from the provided dict.
        Returns the full, real path to the file.
        """
        realpath = os.path.join(self.srcdir, *filepath)
        if not os.path.exists(os.path.dirname(realpath)):
            os.makedirs(os.path.dirname(realpath))
        shutil.copy(os.path.join('rsrc', 'full.mp3'), realpath)

        f = mediafile.MediaFile(realpath)
        for attr in metadata:
            setattr(f, attr, metadata[attr])
        f.save()

        return realpath

    def _run_import(self, titles=TEST_TITLES, delete=False):
        # Make a bunch of tracks to import.
        paths = []
        for i, title in enumerate(titles):
            paths.append(self._create_test_file(
                ['the_album', 'track_%s.mp3' % (i+1)],
                {
                    'track': (i+1),
                    'artist': 'The Artist',
                    'album': 'The Album',
                    'title': title,
                }))

        # Run the UI "beet import" command!
        commands.import_files(
                lib=self.lib,
                paths=[os.path.dirname(paths[0])],
                copy=True,
                write=True,
                autot=False,
                logpath=None,
                art=False,
                threaded=False,
                color=False,
                delete=delete,
                quiet=True,
                resume=False,
                quiet_fallback='skip',
        )

        return paths

    def test_album_created_with_track_artist(self):
        self._run_import()
        albums = self.lib.albums()
        self.assertEqual(len(albums), 1)
        self.assertEqual(albums[0].albumartist, 'The Artist')

    def test_import_copy_arrives(self):
        self._run_import()
        artist_folder = os.path.join(self.libdir, 'The Artist')
        album_folder = os.path.join(artist_folder, 'The Album')
        self.assertEqual(len(os.listdir(artist_folder)), 1)
        self.assertEqual(len(os.listdir(album_folder)), 3)

        filenames = set(os.listdir(album_folder))
        destinations = set('%s.mp3' % title for title in TEST_TITLES)
        self.assertEqual(filenames, destinations)

    def test_import_no_delete(self):
        paths = self._run_import(['sometrack'], delete=False)
        self.assertTrue(os.path.exists(paths[0]))

    def test_import_with_delete(self):
        paths = self._run_import(['sometrack'], delete=True)
        self.assertFalse(os.path.exists(paths[0]))

class ListTest(unittest.TestCase):
    def setUp(self):
        self.io = _common.DummyIO()
        self.io.install()

        self.lib = library.Library(':memory:')
        i = _common.item()
        self.lib.add(i)
        self.lib.add_album([i])

    def tearDown(self):
        self.io.restore()
        
    def test_list_outputs_item(self):
        commands.list_items(self.lib, '', False)
        out = self.io.getoutput()
        self.assertTrue(u'the title' in out)

    def test_list_album_outputs_something(self):
        commands.list_items(self.lib, '', True)
        out = self.io.getoutput()
        self.assertGreater(len(out), 0)
    
    def test_list_album_omits_title(self):
        commands.list_items(self.lib, '', True)
        out = self.io.getoutput()
        self.assertTrue(u'the title' not in out)

    def test_list_uses_track_artist(self):
        commands.list_items(self.lib, '', False)
        out = self.io.getoutput()
        self.assertTrue(u'the artist' in out)
        self.assertTrue(u'the album artist' not in out)
    
    def test_list_album_uses_album_artist(self):
        commands.list_items(self.lib, '', True)
        out = self.io.getoutput()
        self.assertTrue(u'the artist' not in out)
        self.assertTrue(u'the album artist' in out)

class RemoveTest(unittest.TestCase):
    def setUp(self):
        self.io = _common.DummyIO()
        self.io.install()

        self.libdir = os.path.join('rsrc', 'testlibdir')
        os.mkdir(self.libdir)

        # Copy a file into the library.
        self.lib = library.Library(':memory:', self.libdir)
        self.i = library.Item.from_path(os.path.join('rsrc', 'full.mp3'))
        self.lib.add(self.i, True)

    def tearDown(self):
        self.io.restore()
        shutil.rmtree(self.libdir)

    def test_remove_items_no_delete(self):
        self.io.addinput('y')
        commands.remove_items(self.lib, '', False, False)
        items = self.lib.items()
        self.assertEqual(len(list(items)), 0)
        self.assertTrue(os.path.exists(self.i.path))

    def test_remove_items_with_delete(self):
        self.io.addinput('y')
        commands.remove_items(self.lib, '', False, True)
        items = self.lib.items()
        self.assertEqual(len(list(items)), 0)
        self.assertFalse(os.path.exists(self.i.path))

class PrintTest(unittest.TestCase):
    def setUp(self):
        self.io = _common.DummyIO()
        self.io.install()
    def tearDown(self):
        self.io.restore()
    
    def test_print_without_locale(self):
        lang = os.environ.get('LANG')
        if lang:
            del os.environ['LANG']

        try:
            ui.print_(u'something')
        except TypeError:
            self.fail('TypeError during print')
        finally:
            if lang:
                os.environ['LANG'] = lang

    def test_print_with_invalid_locale(self):
        old_lang = os.environ.get('LANG')
        os.environ['LANG'] = ''
        old_ctype = os.environ.get('LC_CTYPE')
        os.environ['LC_CTYPE'] = 'UTF-8'

        try:
            ui.print_(u'something')
        except ValueError:
            self.fail('ValueError during print')
        finally:
            if old_lang:
                os.environ['LANG'] = old_lang
            else:
                del os.environ['LANG']
            if old_ctype:
                os.environ['LC_CTYPE'] = old_ctype
            else:
                del os.environ['LC_CTYPE']

class AutotagTest(unittest.TestCase):
    def setUp(self):
        self.io = _common.DummyIO()
        self.io.install()
    def tearDown(self):
        self.io.restore()

    def _no_candidates_test(self, result):
        task = importer.ImportTask(
            'toppath',
            'path',
            [_common.item()],
        )
        task.set_match('artist', 'album', [], autotag.RECOMMEND_NONE)
        res = commands.choose_match(task, _common.iconfig(None, quiet=False))
        self.assertEqual(res, result)
        self.assertTrue('No match' in self.io.getoutput())

    def test_choose_match_with_no_candidates_skip(self):
        self.io.addinput('s')
        self._no_candidates_test(importer.action.SKIP)

    def test_choose_match_with_no_candidates_asis(self):
        self.io.addinput('u')
        self._no_candidates_test(importer.action.ASIS)

class InputTest(unittest.TestCase):
    def setUp(self):
        self.io = _common.DummyIO()
        self.io.install()
    def tearDown(self):
        self.io.restore()

    def test_manual_search_gets_unicode(self):
        self.io.addinput('\xc3\x82me')
        self.io.addinput('\xc3\x82me')
        artist, album = commands.manual_search()
        self.assertEqual(artist, u'\xc2me')
        self.assertEqual(album, u'\xc2me')

class ConfigTest(unittest.TestCase):
    def setUp(self):
        self.test_cmd = ui.Subcommand('test', help='test')
        commands.default_commands.append(self.test_cmd)
    def tearDown(self):
        commands.default_commands.pop()
    def _run_main(self, args, config, func):
        self.test_cmd.func = func
        ui.main(args + ['test'], StringIO(config))

    def test_paths_section_respected(self):
        def func(lib, config, opts, args):
            self.assertEqual(lib.path_formats['x'], 'y')
        self._run_main([], textwrap.dedent("""
            [paths]
            x=y"""), func)

    def test_default_paths_preserved(self):
        def func(lib, config, opts, args):
            self.assertEqual(lib.path_formats['default'],
                             ui.DEFAULT_PATH_FORMATS['default'])
        self._run_main([], textwrap.dedent("""
            [paths]
            x=y"""), func)

    def test_default_paths_overriden_by_legacy_path_format(self):
        def func(lib, config, opts, args):
            self.assertEqual(lib.path_formats['default'], 'x')
            self.assertEqual(len(lib.path_formats), 1)
        self._run_main([], textwrap.dedent("""
            [beets]
            path_format=x"""), func)

    def test_paths_section_overriden_by_cli_switch(self):
        def func(lib, config, opts, args):
            self.assertEqual(lib.path_formats['default'], 'z')
            self.assertEqual(len(lib.path_formats), 1)
        self._run_main(['-p', 'z'], textwrap.dedent("""
            [paths]
            x=y"""), func)

def suite():
    return unittest.TestLoader().loadTestsFromName(__name__)

if __name__ == '__main__':
    unittest.main(defaultTest='suite')
