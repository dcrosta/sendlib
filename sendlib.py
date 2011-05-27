# -*- coding: utf-8 -*-

"""
Copyright (c) 2011, Daniel Crosta <dcrosta@late.am>
All rights reserved.

Redistribution and use in source and binary forms, with or without
modification, are permitted provided that the following conditions are met:

- Redistributions of source code must retain the above copyright notice,
  this list of conditions and the following disclaimer.

- Redistributions in binary form must reproduce the above copyright notice,
  this list of conditions and the following disclaimer in the documentation
  and/or other materials provided with the distribution.

- Neither the name of the author nor the names of its contributors may be
  used to endorse or promote products derived from this software without
  specific prior written permission.

THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE
LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
POSSIBILITY OF SUCH DAMAGE.
"""

__all__ = ('parse', )

import codecs
import os
import re
import struct

PREFIX = {
    'str': 'S',
    'int': 'I',
    'float': 'F',
    'bool': 'B',
    'data': 'D',
    'nil': 'N',
    'message': 'M',
}
RPREFIX = dict((v, k) for k, v in PREFIX.items())

class Writer(object):
    def __init__(self, definition, stream):
        self.header = definition[0]
        self.definition = definition[1]
        self.stream = stream
        self._pos = -1

    def _check_str(self, value):
        return type(value) in (str, unicode)

    def _check_int(self, value):
        return type(value) in (int, long)

    def _check_bool(self, value):
        return type(value) == bool

    def _check_float(self, value):
        return type(value) == float

    def _check_nil(self, value):
        return value is None

    def _check_data(self, value):
        r = hasattr(value, 'read') and callable(value.read)
        s = hasattr(value, 'seek') and callable(value.seek)
        t = hasattr(value, 'tell') and callable(value.tell)
        if not (r and s and t):
            return False
        value.seek(0, os.SEEK_END)
        length = value.tell()
        if length > 4294967295:
            raise ValueError('cannot accept file-like objects longer than 4294967295 bytes for data')
        return True

    def _check(self, fieldname, value):
        pos = max(0, self._pos)
        defn = self.definition[pos]
        name, typenames = defn
        if name != fieldname:
            if 'nil' in typenames:
                self._write_nil(None)
                self._pos += 1
                return self._check(fieldname, value)
            raise ValueError('Attempting to access field "%s", but should be "%s"' % (fieldname, name))
        for typename in typenames:
            checker = getattr(self, '_check_' + typename)
            result = checker(value)
            if result:
                return typename
        raise ValueError('%s does not match message spec "%s"' % (value, defn))

    def _write_str(self, value):
        value = codecs.encode(value, 'utf-8')
        self.stream.write(PREFIX['str'])
        self.stream.write(struct.pack('>L', len(value)))
        self.stream.write(value)

    def _write_int(self, value):
        self.stream.write(PREFIX['int'])
        self.stream.write(struct.pack('>L', value))

    def _write_bool(self, value):
        self.stream.write(PREFIX['bool'])
        self.stream.write('t' if value else 'f')

    def _write_nil(self, value):
        self.stream.write(PREFIX['nil'])

    def _write_float(self, value):
        self.stream.write(PREFIX['float'])
        self.stream.write(struct.pack('>d', value))

    def _write_data(self, value):
        value.seek(0, os.SEEK_END)
        length = value.tell()
        value.seek(0, 0)

        self.stream.write(PREFIX['data'])
        self.stream.write(struct.pack('>L', length))

        sofar = 0
        size = 256 * 1024
        while sofar < length:
            amount = min(size, (length - sofar))
            buf = value.read(amount)
            self.stream.write(buf)
            sofar += len(buf)

    def write(self, fieldname, value):
        typename = self._check(fieldname, value)
        if self._pos == -1:
            # write header
            self.stream.write('M')
            self._write_str(self.header[0])
            self._write_int(self.header[1])
            self._pos = 0

        writer = getattr(self, '_write_' + typename)
        writer(value)
        self._pos += 1

class Data(object):
    def __init__(self, length, stream):
        self.pos = 0
        self.length = length
        self.stream = stream

    def read(self, size):
        if self.pos >= self.length:
            return ''
        amount = min(size, (self.length - self.pos))
        out = self.stream.read(amount)
        self.pos += len(out)
        return out

    def readline(self, size=None):
        if self.pos >= self.length:
            return ''
        if size:
            amount = min(size, (self.length - self.pos))
        else:
            amount = self.length - self.pos
        out = self.stream.readline(amount)
        self.pos += len(out)
        return out

    def skip(self):
        self.stream.seek(self.bytes_remaining(), os.SEEK_CUR)
        self.pos = self.length

    def bytes_remaining(self):
        return self.length - self.pos

class Reader(object):
    def __init__(self, definition, stream):
        self.header = definition[0]
        self.definition = definition[1]
        self.stream = stream
        self._pos = -1
        self._data = None

    def _check(self, fieldname, peek):
        defn = self.definition[self._pos]
        name, typenames = defn
        if name != fieldname:
            raise ValueError('Attempting to access field "%s", but should be "%s"' % (fieldname, name))
        typename = RPREFIX[peek]
        if typename in typenames:
            return typename
        raise ValueError('%s does not match message spec "%s"' % (peek, defn))

    def _read_str(self):
        length = self._read_int()
        parts = []
        sofar = 0
        while sofar < length:
            amount = min(2048, (length - sofar))
            buf = self.stream.read(amount)
            sofar += len(buf)
            parts.append(unicode(buf, 'utf-8'))
        return u''.join(parts)

    def _read_int(self):
        return struct.unpack('>L', self.stream.read(struct.calcsize('>L')))[0]

    def _read_bool(self):
        return self.stream.read(1) == 't'

    def _read_nil(self):
        return None

    def _read_float(self):
        return struct.unpack('>d', self.stream.read(struct.calcsize('>d')))[0]

    def _read_data(self):
        length = self._read_int()
        self._data = Data(length, self.stream)
        return self._data

    def read(self, fieldname):
        if self._pos == -1:
            if PREFIX['message'] != self.stream.read(1):
                raise ValueError('Invalid message format')
            if PREFIX['str'] != self.stream.read(1):
                raise ValueError('Invalid message format')
            message = self._read_str()
            if PREFIX['int'] != self.stream.read(1):
                raise ValueError('Invalid message format')
            version = self._read_int()
            if message != self.header[0] or version != self.header[1]:
                raise ValueError('Reader for (%s, %d) cannot read message of type (%s, %d)' % (
                    repr(self.header[0]), self.header[1], message, version))
            self._pos = 0

        if self._data is not None:
            if self._data.bytes_remaining() == 0:
                self._data = None
            else:
                raise Exception('cannot read field, cursor still on data')

        peek = self.stream.read(1)
        typename = self._check(fieldname, peek)
        reader = getattr(self, '_read_' + typename)
        value = reader()
        self._pos += 1
        return value

class Message(object):
    def __init__(self, definition):
        self.definition = definition

    def reader(self, in_stream):
        return Reader(self.definition, in_stream)

    def writer(self, out_stream):
        return Writer(self.definition, out_stream)

def parse(definition_str):
    message = re.compile(r'^\((\w+),\s*(\d+)\):$')
    field = re.compile(r'^-\s*([^:]+):\s+(.+)$')
    _or = re.compile('\s*or\s*')

    messages = {}
    curr = None
    for line in definition_str.split('\n'):
        line = line.strip()
        if line == '' or line.startswith('#'):
            continue

        m = message.match(line)
        if m:
            # new message definition
            name, vers = m.group(1), int(m.group(2))
            if (name, vers) in messages:
                raise Exception('Message (%s, %d) already defined' % (name, vers))
            curr = messages[(name, vers)] = []
            continue

        f = field.match(line)
        if f:
            fieldname = f.group(1)
            typenames = _or.split(f.group(2))
            curr.append((fieldname, typenames))

    for key in messages:
        messages[key] = Message((key, messages[key]))

    return messages


