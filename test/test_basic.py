# -*- coding: utf-8 -*-

import os
import string
from StringIO import StringIO
import unittest

import sendlib

class BasicTests(unittest.TestCase):

    def test_parse(self):
       definition = """
       (foo, 1):
         - bar: str
         - baz: str

       (foo2, 1):
         - bar: int
         - baz: float
       """

       msgs = sendlib.parse(definition)
       self.assertEqual(2, len(msgs))

       expected = sendlib.Message(
           (('foo', 1), [('bar', ['str']), ('baz', ['str'])])
       )
       self.assertEqual(expected.definition, msgs[('foo', 1)].definition)

    def test_write(self):
        definition = """
        (foo, 1):
          - bar: str
          - baz: str or nil
          - qux: str or nil
        """

        msgs = sendlib.parse(definition)
        msg = msgs[('foo', 1)]

        buf = StringIO()
        writer = msg.writer(buf)
        writer.write('bar', 'BAR')
        writer.write('baz', 'BAZ')
        writer.write('qux', 'QUX')

        expected = 'MS\x00\x00\x00\x03fooI\x00\x00\x00\x01S\x00\x00\x00\x03BARS\x00\x00\x00\x03BAZS\x00\x00\x00\x03QUX'
        self.assertEqual(expected, buf.getvalue())

        buf = StringIO()
        writer = msg.writer(buf)
        writer.write('bar', 'BAR')
        writer.write('baz', 'BAZ')
        writer.write('qux', None)

        expected = 'MS\x00\x00\x00\x03fooI\x00\x00\x00\x01S\x00\x00\x00\x03BARS\x00\x00\x00\x03BAZN'
        self.assertEqual(expected, buf.getvalue())

        buf = StringIO()
        writer = msg.writer(buf)
        writer.write('bar', 'BAR')
        writer.write('baz', None)
        writer.write('qux', 'QUX')

        expected = 'MS\x00\x00\x00\x03fooI\x00\x00\x00\x01S\x00\x00\x00\x03BARNS\x00\x00\x00\x03QUX'
        self.assertEqual(expected, buf.getvalue())

        buf = StringIO()
        writer = msg.writer(buf)
        writer.write('bar', 'BAR')
        writer.write('qux', 'QUX')

        expected = 'MS\x00\x00\x00\x03fooI\x00\x00\x00\x01S\x00\x00\x00\x03BARNS\x00\x00\x00\x03QUX'
        self.assertEqual(expected, buf.getvalue())

    def test_write_then_read(self):
        definition = """
        (auth, 1):
          - username: str
          - password: str
        """
        msgs = sendlib.parse(definition)

        buf = StringIO()
        auth = msgs[('auth', 1)].writer(buf)
        auth.write('username', 'dcrosta')
        auth.write('password', 'abc123')

        buf.seek(0, 0)
        reader = msgs[('auth', 1)].reader(buf)
        self.assertEqual('dcrosta', reader.read('username'))
        self.assertEqual('abc123', reader.read('password'))

    def test_write_data(self):
        definition = """
        (msg, 1):
          - data: data
        (msg, 2):
          - data: data
          - after: str
        """
        msgs = sendlib.parse(definition)
        msg = msgs[('msg', 1)]

        # about a megabyte of data
        mydata = StringIO()
        for i in xrange(16900):
            mydata.write(string.letters + string.digits + '\n')
        mydata.seek(0, 0)

        buf = StringIO()
        writer = msg.writer(buf)
        writer.write('data', mydata)

        buf.seek(0, 0)
        reader = msg.reader(buf)
        data_fp = reader.read('data')

        read_data = []
        sofar = 0
        while True:
            out = data_fp.read(256 * 1024)
            if out == '':
                break
            sofar += len(out)
            read_data.append(out)

        mydata.seek(0, 0)
        self.assertEqual(len(mydata.getvalue()), len(''.join(read_data)))
        self.assertEqual(mydata.getvalue(), ''.join(read_data))

        msg = msgs[('msg', 2)]
        buf = StringIO()
        writer = msg.writer(buf)
        mydata.seek(0, 0)
        writer.write('data', mydata)
        writer.write('after', 'hello, world')

        buf.seek(0, 0)
        reader = msg.reader(buf)
        data_fp = reader.read('data')
        data_fp.read(1024)

        self.assertRaises(Exception, reader.read, 'after')
        data_fp.skip()
        self.assertEqual('hello, world', reader.read('after'))

    def test_unicode(self):
        description = """
        (foo, 1):
          - bar: str
        """

        msgs = sendlib.parse(description)
        msg = msgs[('foo', 1)]

        buf = StringIO()
        msg.writer(buf).write('bar', u'åéîøü')

        buf.seek(0, 0)
        actual = msg.reader(buf).read('bar')

        self.assertEqual(unicode, type(actual))
        self.assertEqual(u'åéîøü', actual)

    def test_float(self):
        description = """
        (foo, 1):
          - bar: float
        """

        msgs = sendlib.parse(description)
        msg = msgs[('foo', 1)]

        buf = StringIO()
        msg.writer(buf).write('bar', 1.5)

        buf.seek(0, 0)
        self.assertAlmostEqual(1.5, msg.reader(buf).read('bar'))

    def test_int(self):
        description = """
        (foo, 1):
          - bar: int
        """

        msgs = sendlib.parse(description)
        msg = msgs[('foo', 1)]

        buf = StringIO()
        msg.writer(buf).write('bar', 1)

        buf.seek(0, 0)
        self.assertEqual(1, msg.reader(buf).read('bar'))

    def test_bool(self):
        description = """
        (foo, 1):
          - bar: bool
        """

        msgs = sendlib.parse(description)
        msg = msgs[('foo', 1)]

        buf = StringIO()
        msg.writer(buf).write('bar', True)

        buf.seek(0, 0)
        self.assertTrue(msg.reader(buf).read('bar'))

        buf = StringIO()
        msg.writer(buf).write('bar', False)

        buf.seek(0, 0)
        self.assertFalse(msg.reader(buf).read('bar'))

