import json
import os.path

from pywikiapi import AttrDict


class Cache:
    def __init__(self, filename):
        self.filename = filename
        self._data = None

    def get(self, no_generation=False):
        if not self._data:
            self._reload()
        if not self._data and not no_generation:
            # generator could produce the same data, but it is better to round-trip to disk to ensure consistency
            self.regenerate()
            self._reload()
        if self._data is None and not no_generation:
            self._data = ValueError('Unable to generate data')
        if type(self._data) is ValueError and not no_generation:
            raise self._data
        return self._data

    def _reload(self):
        try:
            self._data = self.load()
        except IOError:
            self._data = None

    def regenerate(self, append=False):
        print(f'----------------  {"APPENDING TO" if append else "REGENERATING"} {self.filename}  ----------------')
        self._data = None
        self.generate(append)

    def load(self):
        raise Exception('Not implemented by derived class')

    def generate(self, append=False):
        raise Exception('Not implemented by derived class')


class CacheJsonl(Cache):

    def __init__(self, filename):
        super().__init__(filename)
        self.object_hook = AttrDict

    def load(self):
        with open(self.filename, "r", encoding='utf-8') as file:
            items = []
            for line in file.readlines():
                line = line.rstrip()
                if not line:
                    continue
                items.append(json.loads(line, object_hook=self.object_hook))
            return items

    def iter(self):
        if not os.path.isfile(self.filename):
            self.regenerate()

        with open(self.filename, "r", encoding='utf-8') as file:
            for line in file:
                line = line.rstrip()
                if line:
                    yield json.loads(line)


class CacheInMemory:
    def __init__(self):
        self._is_loaded = False
        self._data = None

    def get(self):
        if self._is_loaded:
            return self._data
        self._data = self.generate()
        self._is_loaded = True
        return self._data

    def regenerate(self):
        self._is_loaded = False

    def generate(self):
        raise Exception('Not implemented by derived class')
