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

__version__ = '0.2'
__all__ = ('SendlibError', 'ParseError', 'parse', '__version__')

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

class SendlibError(Exception): pass
class ParseError(SendlibError): pass

# a special marker, distinct from None
Nothing = type('Nothing', (), {})()

class Writer(object):
    __slots__ = ('message', 'stream', '_pos')
    def __init__(self, message, stream):
        self.message = message
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
            raise SendlibError(
                'data length must be less than 4294967295 bytes')
        return True

    def _check(self, fieldname, value):
        pos = max(0, self._pos)
        field = self.message.fields[pos]
        if fieldname != field.name:
            if 'nil' in field.types:
                # FIXME: this is shady, a method named
                # _check should not write anything
                self._write_nil(None)
                self._pos += 1
                return self._check(fieldname, value)
            raise SendlibError(
                'Attempting to access field "%s", but should be "%s"' %
                (fieldname, field.name))
        for type in field.types:
            if isinstance(type, Message):
                if value is Nothing or value == type:
                    return 'msg'
                continue
            checker = getattr(self, '_check_' + type)
            result = checker(value)
            if result:
                return type
        raise SendlibError(
            '%s does not match message spec "%s"' % (repr(value), field.spec))

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

    def _write_msg(self, value):
        field = self.message.fields[self._pos]
        if value is Nothing:
            # assume exactly one Message in types
            message = tuple(t for t in field.types if isinstance(t, Message))[0]
        else:
            # value will be a Message instance
            message = tuple(t for t in field.types if value == t)[0]
        writer = message.writer(self.stream)
        return writer

    def write(self, fieldname, value=Nothing):
        type = self._check(fieldname, value)
        if self._pos == -1:
            # write header
            self.stream.write('M')
            self._write_str(self.message.name)
            self._write_int(self.message.version)
            self._pos = 0

        writer = getattr(self, '_write_' + type)
        out = writer(value)
        self._pos += 1
        return out

class Data(object):
    __slots__ = ('length', 'stream', '_pos')
    def __init__(self, length, stream):
        self.length = length
        self.stream = stream
        self._pos = 0

    def read(self, size):
        if self._pos >= self.length:
            return ''
        amount = min(size, (self.length - self._pos))
        out = self.stream.read(amount)
        self._pos += len(out)
        return out

    def readline(self, size=None):
        if self._pos >= self.length:
            return ''
        if size:
            amount = min(size, (self.length - self._pos))
        else:
            amount = self.length - self._pos
        out = self.stream.readline(amount)
        self._pos += len(out)
        return out

    def skip(self):
        self.stream.seek(self.bytes_remaining(), os.SEEK_CUR)
        self._pos = self.length

    def bytes_remaining(self):
        return self.length - self._pos

class Reader(object):
    __slots__ = ('message', 'stream', '_pos', '_data', '_peek')
    def __init__(self, message, stream):
        self.message = message
        self.stream = stream
        self._pos = -1
        self._data = None
        self._peek = None

    def _check(self, fieldname):
        pos = max(0, self._pos)
        field = self.message.fields[pos]
        if field.name != fieldname:
            raise SendlibError(
                'Attempting to access field "%s", but should be "%s"' %
                (fieldname, field.name))
        try:
            type = RPREFIX[self._peek]
        except KeyError:
            raise SendlibError('unknown field prefix "%s"' % self._peek)
        if type in field.types:
            return type
        raise SendlibError(
            'field type "%s" incorrect for field %s' % (type, field))

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
            self._pos = 0
            if PREFIX['message'] != self.stream.read(1):
                raise SendlibError('Invalid message format')
            if PREFIX['str'] != self.stream.read(1):
                raise SendlibError('Invalid message format')
            name = self._read_str()
            if PREFIX['int'] != self.stream.read(1):
                raise SendlibError('Invalid message format')
            version = self._read_int()
            if name != self.message.name or version != self.message.version:
                raise SendlibError(
                    'Reader for %s cannot read message of type (%s, %d)'
                    % (self.message, name, version))

        if self._data is not None:
            if self._data.bytes_remaining() == 0:
                self._data = None
            else:
                raise Exception('cannot read field, cursor still on data')

        if self._peek is None:
            self._peek = self.stream.read(1)
        typename = self._check(fieldname)
        reader = getattr(self, '_read_' + typename)
        value = reader()
        self._pos += 1
        self._peek = None
        return value

_or = re.compile(r'\s*or\s*')
_msg = re.compile(r'msg\s*\(\s*(\w+),\s*(\d+)\s*\)')
class Field(object):
    """
    Field contains the definition of a single field. ``name`` is
    the expected field name, and ``types`` is a tuple of valid
    type names for the field.

    >>> f = Field('foo', 'str or nil')
    >>> f.name
    'foo'
    >>> f.types
    ('str', 'nil')
    """

    __slots__ = ('message', 'name', 'types', 'spec')
    def __init__(self, message, name, types):
        self.message = message
        self.name = name
        self.spec = types
        self.types = []
        for type in tuple(_or.split(types)):
            msgref = _msg.match(type)
            if msgref:
                submsg = self.message.registry.get_message(
                    msgref.group(1),
                    int(msgref.group(2))
                )
                if not submsg:
                    raise ParseError(
                        'unknown referenced message "%s"' %
                        (msgref.group(1), int(msgref.group(2))))
                self.types.append(submsg)
            elif type not in PREFIX:
                raise ParseError('unknown field type "%s"' % type)
            else:
                self.types.append(type)
        self.types = tuple(self.types)

    def __repr__(self):
        return 'Field(%s, %s)' % (repr(self.name), self.types)

class Message(object):
    """
    Message encapsulates the definition of a single message.
    ``name`` is the message name, ``version`` is the message
    version, and ``fields`` is a tuple of :class:`Field`
    objects for each field.

    >>> m = Message('foo', 1, (('i', 'int'), ('sn', 'str or nil')))
    >>> m.name
    'foo'
    >>> m.version
    1
    >>> m.fields
    (Field('i', ('int', )), Field('sn', ('str', 'nil')))
    """

    __slots__ = ('registry', 'name', 'version', 'fields')
    def __init__(self, registry, name, version, fields):
        self.registry = registry
        self.name = name
        self.version = version
        self.fields = fields

    def reader(self, in_stream):
        """
        Return a :class:`Reader` object which reads messages of
        this format from ``in_stream``. ``in_stream`` must have
        a ``read(size)`` method.
        """
        return Reader(self, in_stream)

    def writer(self, out_stream):
        """
        Return a :class:`Writer` object which writes messages of
        this format to ``out_stream``. ``out_stream`` must have
        a ``write(str)`` method.
        """
        return Writer(self, out_stream)


class MessageRegistry(object):
    """
    A :class:`MessageRegistry` contains the result of a call to
    :func:`parse`, and is the main interface for receiving and
    sending messages.

    Messages can be retrieved programmatically from the :class:
    `MessageRegistry` by dict-like access (using the ``[]``
    operator), or by ``name`` and ``version`` using :meth:
    `get_message`.
    """

    __slots__ = ('messages', )
    def __init__(self, messages):
        self.messages = messages

    def __getitem__(self, key):
        """
        Retrieve the :class:`Message` whose name and version match
        the given key. ``key`` is a tuple of ``(name, version)``.
        Raises :class:`KeyError` if no such message exists.
        """
        return self.messages[key]

    def get_message(self, name, version=1):
        """
        Retrieve the :class:`Message` whose name and version match
        ``name`` and ``version``, or return ``None`` if no such
        message exists.
        """
        try:
            return self[(name, version)]
        except KeyError:
            return None

def parse(definition_str):
    message = re.compile(r'^\((\w+),\s*(\d+)\):$')
    field = re.compile(r'^-\s*([^:]+):\s+(.+)$')

    registry = MessageRegistry({})
    messages = registry.messages
    curr = None
    names = None
    for lineno, line in enumerate(definition_str.split('\n')):
        line = line.strip()
        if line == '' or line.startswith('#'):
            continue

        f = field.match(line)
        if f:
            if curr is None:
                raise ParseError(
                    'field definition outside of message at line %d' % lineno)
            name = f.group(1)
            type = f.group(2)
            if name not in names:
                f = Field(curr, name, type)
                curr.fields.append(f)
                names.add(name)
            else:
                raise ParseError(
                    'duplicate field name "%s" at line %d' % (name, lineno))
            continue

        m = message.match(line)
        if m:
            # new message definition
            name, vers = m.group(1), int(m.group(2))
            if (name, vers) in messages:
                raise ParseError('Duplicate message (%s, %d)' % (name, vers))
            curr = messages[(name, vers)] = Message(registry, name, vers, [])
            names = set()
            continue

    for message in registry.messages.values():
        message.fields = tuple(message.fields)

    return registry


