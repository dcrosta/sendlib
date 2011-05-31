# -*- coding: utf-8 -*-

# Copyright (c) 2011, Daniel Crosta <dcrosta@late.am>
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
# - Redistributions of source code must retain the above copyright notice,
#   this list of conditions and the following disclaimer.
#
# - Redistributions in binary form must reproduce the above copyright notice,
#   this list of conditions and the following disclaimer in the documentation
#   and/or other materials provided with the distribution.
#
# - Neither the name of the author nor the names of its contributors may be
#   used to endorse or promote products derived from this software without
#   specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.

__version__ = '0.2.1'
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
LIST_PREFIX = 'L'

class SendlibError(Exception): pass
class ParseError(SendlibError): pass

# a special marker, distinct from None
class Nothing(object):
    def __repr__(self):
        return 'Nothing'
Nothing = Nothing()

def typename(obj):
    if obj is None:
        return 'nil'
    elif isinstance(obj, Message):
        return 'msg (%s, %d)' % (obj.name, obj.version)
    return str(type(obj).__name__)

class Writer(object):
    """
    A :class:`Writer` is bound to a specific stream and
    :class:`Message`, and maintains internal state for writing
    a single instance of that message to the stream.

    You ordinarily obtain a :class:`Writer` instance by calling
    :meth:`Message.writer` on a :class:`Message` instance, not
    by directly constructing one.
    """

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
        if pos >= len(self.message.fields):
            raise SendlibError('attempt to write past end of message')
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
        if type(value) in (tuple, list):
            return self._check_list(field, value)
        elif value == Nothing or \
             type(value) in (str, unicode) and _msg.match(value) or \
             isinstance(value, Message):
            return self._check_msg(field, value)
        for type_name in field.types:
            if _msg.match(type_name):
                continue
            if _many.match(type_name):
                continue
            checker = getattr(self, '_check_' + type_name)
            result = checker(value)
            if result:
                return type_name
        raise SendlibError(
            '%s does not match field spec "%s"' % (repr(value), field.spec))

    def _check_list(self, field, sequence):
        # make sure the sequence has all
        # of the same type
        if len(sequence) == 0:
            return 'list'
        types_found = set()
        for item in sequence:
            types_found.add(typename(item))
        if len(types_found) > 1:
            raise SendlibError(
                'sequence arguments to write must contain elements of '
                'compatible types, found %s' % list(types_found))
        inner_type = types_found.pop()
        many_type = 'many ' + inner_type

        for type_name in field.types:
            if not _many.match(type_name):
                continue
            if many_type == type_name:
                return 'list'
        # not sure we can get here
        raise SendlibError(
            '%s does not match field spec "%s"' % (repr(sequence), field.spec))

    def _check_msg(self, field, value):
        # ensure that value is one of the messages,
        # or if value is Nothing, that there's only
        # one message type for this field
        if isinstance(value, Message):
            value = 'msg (%s, %s)' % (value.name, value.version)
        if type(value) in (str, unicode):
            m = _msg.match(value)
            if not m:
                raise SendlibError('value should be (message_name, version)')
            msg = self.message.registry.get_message(
                m.group(1), int(m.group(2)))
            if not msg:
                raise SendlibError(
                    'unknown message (%s, %s)' % (m.group(1), m.group(2)))
            type_name = 'msg (%s, %s)' % (m.group(1), m.group(2))
            if type_name not in field.types:
                raise SendlibError(
                    'message (%s, %s) not valid for field %s' %
                    (m.group(1), m.group(2)), field.name)
            return 'msg'
        elif value == Nothing:
            num = len([t for t in field.types if _msg.match(t)])
            if num == 0:
                raise SendlibError(
                    'messages not valid for field %s' % field.name)
            elif num > 1:
                raise SendlibError(
                    'more than one message valid for field %s' % field.name)
            return 'msg'

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
        if isinstance(value, Message):
            value = 'msg (%s, %s)' % (value.name, value.version)
        if type(value) in (str, unicode):
            m = _msg.match(value)
            message = self.message.registry.get_message(
                m.group(1), int(m.group(2)))
        elif value is Nothing:
            # assume exactly one Message in types
            m = tuple(t for t in field.types if _msg.match(t))[0]
            m = _msg.match(m)
            message = self.message.registry.get_message(
                m.group(1), int(m.group(2)))
        writer = message.writer(self.stream)
        return writer

    def _write_list(self, value):
        self.stream.write('L')
        self.stream.write(struct.pack('>L', len(value)))
        if len(value):
            inner_type = typename(value[0])
            if _msg.match(inner_type):
                writer = self._write_msg
            else:
                writer = getattr(self, '_write_' + inner_type)
            out = []
            for item in value:
                out.append(writer(item))
            return tuple(out)
        else:
            return ()

    def write(self, fieldname, value=Nothing):
        """
        Write the `value` to the stream, after verifying that
        `fieldname` is the correct next field in the message
        format. `value` defaults to :class:`Nothing`, which is
        distinct from :class:`None`, as :class:`None` is a valid
        value which may be written (when a field is ``or nil``).

        When writing ``many`` fields, `value` should be a list
        or tuple; if not, the single value will be written for
        the field and future writes to that field will fail.

        If a field other than `fieldname` should be written,
        unless all preceding unwritten fields are ``or nil``,
        raise :class:`SendlibError`.

        Returns :class:`None`, except when writing a nested
        :class:`Message`, in which case a new
        :class:`Writer` is returned.
        """
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

    def flush(self):
        self.stream.flush()

class Data(object):
    """
    :class:`Data` is a limited file-like object for reading
    ``data`` elements from message streams. In particular,
    it does not support :meth:`seek`, as ``sendblib`` does
    not require that the underlying stream support full
    bi-directional seeking.
    """
    __slots__ = ('length', 'stream', '_pos')
    def __init__(self, length, stream):
        self.length = length
        self.stream = stream
        self._pos = 0

    def read(self, size=None):
        """
        Read at most `size` bytes of data from the underlying
        stream. If `size` bytes are not available, return as
        many as are available. If past the end of the stream,
        return an empty string.
        """
        if self._pos >= self.length:
            return ''
        if size:
            amount = min(size, (self.length - self._pos))
        else:
            amount = self.length - self._pos
        out = self.stream.read(amount)
        self._pos += len(out)
        return out

    def readline(self, size=None):
        """
        Read a line from the stream, including the trailing
        new line character. If `size` is set, don't read more
        than `size` bytes, even if the result does not represent
        a complete line.

        The last line read may not include a trailing new line
        character if one was not present in the underlying stream.
        """
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
        """
        Advance the internal pointer to the end of the data
        area in the stream. This allows the next call to
        :meth:`Reader.read` to succeed, as though all the
        data had been read by the application.
        """
        self.stream.seek(self.bytes_remaining(), os.SEEK_CUR)
        self._pos = self.length

    def bytes_remaining(self):
        """
        Return the number of bytes remaining.
        """
        return self.length - self._pos

class Reader(object):
    """
    A :class:`Reader` is bound to a specific stream and
    :class:`Message`, and maintains internal state for
    reading a single instance of that message from the
    stream.

    You ordinarily obtain a :class:`Reader` instance by
    calling :meth:`Message.reader` on a :class:`Message`
    instance, not by directly constructing one.
    """

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
        """
        Read the next field from the stream. `fieldname` is used
        to verify that your application logic matches the message
        field order, and if `fieldname` does not match the next
        field in the message definition, :class:`SendlibError`
        is raised.

        Returns a Python object of the correct type, depending on
        the type present in the stream. If the type is ``data``,
        returns a :class:`Data` file-like object.
        """
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
_many = re.compile(r'many\s+(.+?)\s*$')
class Field(object):
    """
    :class:`Field` contains the definition of a single field.

    .. py:attribute:: message

       The :class:`Message` to which this Field belongs

    .. py:attribute:: name

       The name of the :class:`Field`

    .. py:attribute:: types

       :class:`tuple` of type specifiers for this :class:`Field`,
       which may include references to :class:`Message` instances,
       if this :class:`Field` is a nested message field.
    """

    __slots__ = ('message', 'name', 'types', 'spec')
    def __init__(self, message, name, types):
        self.message = message
        self.name = name
        self.spec = types
        self.types = []
        for type in _or.split(types):
            do_many = False
            many = _many.match(type)
            if many:
                type = many.group(1)
                do_many = True

            msgref = _msg.match(type)
            if msgref:
                submsg = self.message.registry.get_message(
                    msgref.group(1),
                    int(msgref.group(2))
                )
                if not submsg:
                    raise ParseError(
                        'unknown referenced message "%s"' %
                        repr((msgref.group(1), int(msgref.group(2)))))

                type = 'msg (%s, %d)' % (submsg.name, submsg.version)
            elif type not in PREFIX:
                raise ParseError('unknown field type "%s"' % type)

            if do_many:
                self.types.append('many ' + type)
            else:
                self.types.append(type)
        self.types = tuple(self.types)

    def __repr__(self):
        return 'Field(%s, %s)' % (repr(self.name), self.types)

class Message(object):
    """
    :class:`Message` contains the definition of a single
    message. `name` is the message name, `version` is the message
    version, and `fields` is a tuple of :class:`Field`
    objects.

    .. py:attribute:: registry

       The :class:`MessageRegistry` that contains this message

    .. py:attribute:: name

       The name of the message

    .. py:attribute:: version

       The version of the message

    .. py:attribute:: fields

       :class:`tuple` of :class:`Field`
    """

    __slots__ = ('registry', 'name', 'version', 'fields')
    def __init__(self, registry, name, version, fields):
        self.registry = registry
        self.name = name
        self.version = version
        self.fields = fields

    def __repr__(self):
        return 'Message(%s, %s, %s)' % (repr(self.name),
                                        self.version,
                                        self.fields)

    def __eq__(self, other):
        return isinstance(other, Message) and \
               self.registry == other.registry and \
               self.name == other.name and \
               self.version == other.version

    def reader(self, in_stream):
        """
        Return a :class:`Reader` object which reads
        messages of this format from `in_stream`. `in_stream`
        must have a ``read(size)`` method.
        """
        return Reader(self, in_stream)

    def writer(self, out_stream):
        """
        Return a :class:`Writer` object which writes
        messages of this format to `out_stream`. `out_stream`
        must have a ``write(str)`` method.
        """
        return Writer(self, out_stream)


class MessageRegistry(object):
    """
    :class:`MessageRegistry` contains the definition of one or
    more messages, and is the main interface for receiving and
    sending messages.
    """

    __slots__ = ('messages', )
    def __init__(self, messages):
        self.messages = messages

    def __getitem__(self, key):
        """
        Retrieve the :class:`Message` whose name and version match
        the given key. `key` is a tuple of ``(name, version)``.
        Raises :class:`KeyError` if no such message exists.
        """
        return self.messages[key]

    def get_message(self, name, version=1):
        """
        Retrieve the :class:`Message` whose name and version match
        `name` and `version`, or return ``None`` if no such
        message exists.
        """
        try:
            return self[(name, version)]
        except KeyError:
            return None

def parse(schema):
    """
    Parse `schema`, either a string or a file-like object, and
    return a :class:`MessageRegistry` with the loaded messages.
    """
    if not isinstance(schema, basestring):
        # assume it is file-like
        schema = schema.read()

    message = re.compile(r'^\(([^,]+),\s*(\d+)\):\s*$')
    field = re.compile(r'^-\s*([^:]+):\s+(.+?)\s*$')

    registry = MessageRegistry({})
    messages = registry.messages
    curr = None
    names = None
    for lineno, line in enumerate(schema.split('\n')):
        line = line.strip()
        if '#' in line:
            line = line[:line.index('#')]
        if line == '':
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
                continue
            else:
                raise ParseError(
                    'duplicate field name "%s" at line %d' % (name, lineno))

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


