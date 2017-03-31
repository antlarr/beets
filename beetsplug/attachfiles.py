from beets.plugins import BeetsPlugin
from beets.util import (bytestring_path, syspath,
                        copy_directory, copy, move_directory, move)
import os
import shutil
import fnmatch


def copy_file_or_directory(src, tgt):
    if os.path.isdir(src):
        copy_directory(src, tgt)
    else:
        copy(src, tgt)


def move_file_or_directory(src, tgt):
    if os.path.isdir(src):
        move_directory(src, tgt)
    else:
        move(src, tgt)


def remove_file_or_directory(path):
    if os.path.isdir(path) and not os.path.islink(path):
        shutil.rmtree(path)
    else:
        os.unlink(path)


class AttachFilesPlugin(BeetsPlugin):
    def __init__(self):
        super(AttachFilesPlugin, self).__init__()
        self.config.add({
            'allow_multiple_copies': False,
            'allow_remove': True
        })
        self.allow_multiple_copies = self.config['allow_multiple_copies']
        self.allow_remove = self.config['allow_remove']

        self.register_listener('album_imported', self.album_imported)
        self.register_listener('item_copied', self.item_copied)
        self.register_listener('item_imported', self.item_imported)
        self.register_listener('item_moved', self.item_moved)
        self.register_listener('item_linked', self.item_linked)
        self.register_listener('item_hardlinked', self.item_hardlinked)
        self.register_listener('item_removed', self.item_removed)
        self.directories_already_imported = []

    def album_imported(self, lib, album):
        self.directories_already_imported = []

    def item_imported(self, item, source, destination):
        self.directories_already_imported = []

    def attach_files(self, source_dir, destination_dir, copy=False,
                     move=False, link=False, hardlink=False):
        if self.allow_multiple_copies:
            identifier = (source_dir, destination_dir)
        else:
            identifier = source_dir

        if identifier in self.directories_already_imported:
            if self.allow_multiple_copies:
                self._log.debug(u"{0} already attached to {1}",
                                source_dir, destination_dir)
            else:
                self._log.debug(u"{0} already attached and multiple copies not"
                                " allowed", source_dir, destination_dir)
            return

        self._log.debug(u"Attaching {0} to {1}", source_dir, destination_dir)

        source_files = os.listdir(source_dir)
        for attachment_pattern in self.config['patterns'].as_str_seq():
            for name in source_files:
                if fnmatch.fnmatch(name, bytestring_path(attachment_pattern)):
                    src = os.path.join(source_dir, name)
                    tgt = os.path.join(destination_dir, name)
                    if copy:
                        copy_file_or_directory(src, tgt)
                    elif move:
                        move_file_or_directory(src, tgt)
                    elif link:
                        print('attach_files by symlinking not implemented yet'
                              '(%s, %s)' % (src, tgt))
                    elif hardlink:
                        print('attach files by hardlinking not implemented yet'
                              '(%s, %s)' % (src, tgt))

        self.directories_already_imported.append(identifier)

    def item_copied(self, item, source, destination):
        source_dir = os.path.dirname(syspath(source))
        destination_dir = os.path.dirname(syspath(destination))
        self.attach_files(source_dir, destination_dir, copy=True)

    def item_moved(self, item, source, destination):
        source_dir = os.path.dirname(source)
        destination_dir = os.path.dirname(destination)
        self.attach_files(source_dir, destination_dir, move=True)

    def item_linked(self, item, source, destination):
        source_dir = os.path.dirname(source)
        destination_dir = os.path.dirname(destination)
        self.attach_files(source_dir, destination_dir, link=True)

    def item_hardlinked(self, item, source, destination):
        source_dir = os.path.dirname(syspath(source))
        destination_dir = os.path.dirname(syspath(destination))
        self.attach_files(source_dir, destination_dir, hardlink=True)

    def item_removed(self, item, delete):
        if not delete or not self.allow_remove:
            return

        directory = os.path.dirname(syspath(item.path))
        try:
            contents = os.listdir(directory)
        except FileNotFoundError:
            return

        removable_contents = [os.path.basename(item.path)]

        for name in contents:
            for attachment_pattern in self.config['patterns'].as_str_seq():
                if fnmatch.fnmatch(name, bytestring_path(attachment_pattern)):
                    removable_contents.append(name)
                    break

        if sorted(removable_contents) == sorted(contents):
            removable_contents = removable_contents[1:]
            self._log.debug(u"Removing attachments in {0} : {1}",
                            directory, removable_contents)

            for name in removable_contents:
                remove_file_or_directory(os.path.join(directory, name))
