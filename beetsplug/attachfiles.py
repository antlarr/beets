from beets.plugins import BeetsPlugin
from beets.util import py3_path, copy_directory, copy, move_directory, move
import os
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


class AttachFilesPlugin(BeetsPlugin):
    def __init__(self):
        super(AttachFilesPlugin, self).__init__()
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
        if source_dir in self.directories_already_imported:
            return

        source_files = [py3_path(x) for x in os.listdir(source_dir)]
        for attachment_pattern in self.config['files'].as_str_seq():
            for name in source_files:
                if fnmatch.fnmatch(name, attachment_pattern):
                    src = os.path.join(py3_path(source_dir), name)
                    tgt = os.path.join(py3_path(destination_dir), name)
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

        self.directories_already_imported.append(source_dir)

    def item_copied(self, item, source, destination):
        source_dir = os.path.dirname(source)
        destination_dir = os.path.dirname(destination)
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
        source_dir = os.path.dirname(source)
        destination_dir = os.path.dirname(destination)
        self.attach_files(source_dir, destination_dir, hardlink=True)

    def item_removed(self, item):
        directory = os.path.dirname(item.path)
        try:
            contents = [py3_path(x) for x in os.listdir(directory)]
        except FileNotFoundError:
            return

        try:
            contents.remove(os.path.basename(item.path))
        except ValueError:
            pass
        for attachment_pattern in self.config['files'].as_str_seq():
            try:
                contents = [name for name in contents
                            if not fnmatch.fnmatch(name, attachment_pattern)]
            except ValueError:
                pass
        if not contents:
            print('Remove %s and the attachments within not implemented yet' % directory)
