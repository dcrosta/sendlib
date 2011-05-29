# -*- coding: utf-8 -*-

import os
from StringIO import StringIO
import unittest

import sendlib

class SerializationTest(unittest.TestCase):

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

    def test_fields_write_in_order(self):
        definition = """
        (foo, 1):
          - bar: str
          - baz: str
          - qux: str
        """

        msgs = sendlib.parse(definition)
        foo = msgs[('foo', 1)]

        writer = foo.writer(StringIO())
        writer.write('bar', '')
        self.assertRaises(sendlib.SendlibError, writer.write, 'qux', '')

    def test_write_past_end(self):
        definition = """
        (foo, 1):
          - bar: str
        """

        msgs = sendlib.parse(definition)
        foo = msgs[('foo', 1)]

        writer = foo.writer(StringIO())
        writer.write('bar', '')
        self.assertRaises(sendlib.SendlibError, writer.write, 'baz', '')

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

    def test_nil(self):
        description = """
        (foo, 1):
          - bar: nil
        """

        msgs = sendlib.parse(description)
        msg = msgs[('foo', 1)]

        buf = StringIO()
        msg.writer(buf).write('bar', None)

        buf.seek(0, 0)
        self.assertEqual(None, msg.reader(buf).read('bar'))

    def test_read_wrong_message(self):
        definition = """
        (foo, 1):
          - bar: str
          - baz: str or nil
          - qux: str or nil

        (bar, 1):
          - foo: int
          - baz: bool
        """

        msgs = sendlib.parse(definition)
        foo = msgs[('foo', 1)]
        bar = msgs[('bar', 1)]

        input = 'MS\x00\x00\x00\x03fooI\x00\x00\x00\x01S\x00\x00\x00\x03BARS\x00\x00\x00\x03BAZS\x00\x00\x00\x03QUX'
        reader = bar.reader(StringIO(input))
        self.assertRaises(sendlib.SendlibError, reader.read, 'foo')

        # this should not raise
        reader = foo.reader(StringIO(input))
        self.assertEqual('BAR', reader.read('bar'))

    def test_read_wrong_field(self):
        definition = """
        (foo, 1):
          - bar: str
          - baz: str
        """
        msgs = sendlib.parse(definition)
        foo = msgs[('foo', 1)]

        input = 'MS\x00\x00\x00\x03fooI\x00\x00\x00\x01S\x00\x00\x00\x03BARS\x00\x00\x00\x03BAZ'
        reader = foo.reader(StringIO(input))

        self.assertRaises(sendlib.SendlibError, reader.read, 'baz')
        self.assertEqual('BAR', reader.read('bar'))
        self.assertRaises(sendlib.SendlibError, reader.read, 'bar')
        self.assertEqual('BAZ', reader.read('baz'))

    def test_nested_message(self):
        definition = """
        (foo, 1):
         - bar: str
         - baz: str

        (baz, 1):
         - foo: msg (foo, 1)
        """
        registry = sendlib.parse(definition)

        baz = registry.get_message('baz')
        buf = StringIO()
        writer = baz.writer(buf)
        foowriter = writer.write('foo')
        foowriter.write('bar', 'hello')
        foowriter.write('baz', 'world')

        expected = 'MS\x00\x00\x00\x03bazI\x00\x00\x00\x01MS\x00\x00\x00\x03fooI\x00\x00\x00\x01S\x00\x00\x00\x05helloS\x00\x00\x00\x05world'
        self.assertEqual(expected, buf.getvalue())

    def test_nested_message_with_or(self):
        definition = """
        (foo, 1):
         - a: str
         - b: str

        (bar, 1):
         - c: int
         - d: int

        (baz, 1):
         - m: msg(foo, 1) or msg(bar, 1)
        """
        registry = sendlib.parse(definition)

        baz = registry.get_message('baz')
        buf = StringIO()
        writer = baz.writer(buf)
        foowriter = writer.write('m', registry.get_message('foo'))
        foowriter.write('a', 'hello')
        foowriter.write('b', 'world')

        expected = 'MS\x00\x00\x00\x03bazI\x00\x00\x00\x01MS\x00\x00\x00\x03fooI\x00\x00\x00\x01S\x00\x00\x00\x05helloS\x00\x00\x00\x05world'
        self.assertEqual(expected, buf.getvalue())

    def test_nested_message_or_nil(self):
        definition = """
        (foo, 1):
         - a: str
         - b: str

        (bar, 1):
         - m: msg(foo, 1) or nil
        """
        registry = sendlib.parse(definition)

        bar = registry.get_message('bar')
        buf = StringIO()
        writer = bar.writer(buf)
        foowriter = writer.write('m', registry.get_message('foo'))
        foowriter.write('a', 'hello')
        foowriter.write('b', 'world')

        expected = 'MS\x00\x00\x00\x03barI\x00\x00\x00\x01MS\x00\x00\x00\x03fooI\x00\x00\x00\x01S\x00\x00\x00\x05helloS\x00\x00\x00\x05world'
        self.assertEqual(expected, buf.getvalue())


        buf = StringIO()
        writer = bar.writer(buf)
        foowriter = writer.write('m', None)

        expected = 'MS\x00\x00\x00\x03barI\x00\x00\x00\x01N'
        self.assertEqual(expected, buf.getvalue())

    def test_fails_on_invalid_prefix(self):
        definition = """
        (foo, 1):
         - a: int
        """
        msgs = sendlib.parse(definition)
        foo = msgs[('foo', 1)]

        serialized = 'MS\x00\x00\x00\x03fooI\x00\x00\x00\x01QI\x00\x00\x00\x01'
        reader = foo.reader(StringIO(serialized))
        self.assertRaises(sendlib.SendlibError, reader.read, 'a')

    def test_wrong_type(self):
        definition = """
        (foo, 1):
         - a: str
        """
        msgs = sendlib.parse(definition)
        foo = msgs[('foo', 1)]

        serialized = 'MS\x00\x00\x00\x03fooI\x00\x00\x00\x01I\x00\x00\x00\x01'
        reader = foo.reader(StringIO(serialized))
        self.assertRaises(sendlib.SendlibError, reader.read, 'a')

    def test_invalid_header(self):
        definition = """
        (foo, 1):
         - a: str
        """
        msgs = sendlib.parse(definition)
        foo = msgs[('foo', 1)]

        serialized = 'XS\x00\x00\x00\x03fooI\x00\x00\x00\x01I\x00\x00\x00\x01'
        reader = foo.reader(StringIO(serialized))
        self.assertRaises(sendlib.SendlibError, reader.read, 'a')

        serialized = 'MX\x00\x00\x00\x03fooI\x00\x00\x00\x01I\x00\x00\x00\x01'
        reader = foo.reader(StringIO(serialized))
        self.assertRaises(sendlib.SendlibError, reader.read, 'a')

        serialized = 'MS\x00\x00\x00\x03fooX\x00\x00\x00\x01I\x00\x00\x00\x01'
        reader = foo.reader(StringIO(serialized))
        self.assertRaises(sendlib.SendlibError, reader.read, 'a')

    def test_flush(self):
        class MockStream(object):
            def __init__(self):
                self.is_flushed = False
            def write(self, data): pass
            def flush(self):
                self.is_flushed = True

        definition = """
        (foo, 1):
         - a: str
        """
        msgs = sendlib.parse(definition)
        foo = msgs[('foo', 1)]

        stream = MockStream()
        writer = foo.writer(stream)
        writer.write('a', 'blah')
        writer.flush()

        self.assertTrue(stream.is_flushed)

    def test_many(self):
        definition = """
        (foo, 1):
         - a: many str
         - b: str
        """

        msgs = sendlib.parse(definition)
        foo = msgs[('foo', 1)]

        buf = StringIO()
        writer = foo.writer(buf)
        writer.write('a', ['hello', 'world'])
        writer.write('b', 'goodbye')

        expected = 'MS\x00\x00\x00\x03fooI\x00\x00\x00\x01L\x00\x00\x00\x02S\x00\x00\x00\x05helloS\x00\x00\x00\x05worldS\x00\x00\x00\x07goodbye'
        self.assertEqual(expected, buf.getvalue())


        buf = StringIO()
        writer = foo.writer(buf)
        writer.write('a', [])
        writer.write('b', 'goodbye')

        expected = 'MS\x00\x00\x00\x03fooI\x00\x00\x00\x01L\x00\x00\x00\x00S\x00\x00\x00\x07goodbye'
        self.assertEqual(expected, buf.getvalue())


        buf = StringIO()
        writer = foo.writer(buf)
        self.assertRaises(sendlib.SendlibError, writer.write, 'a', ['hello', 1])

    def test_many_or_nil(self):
        definition = """
        (foo, 1):
         - a: many str or nil
         - b: str
        """

        msgs = sendlib.parse(definition)
        foo = msgs[('foo', 1)]

        buf = StringIO()
        writer = foo.writer(buf)
        writer.write('a', None)
        writer.write('b', 'goodbye')

        expected = 'MS\x00\x00\x00\x03fooI\x00\x00\x00\x01NS\x00\x00\x00\x07goodbye'
        self.assertEqual(expected, buf.getvalue())

    def test_many_nil(self):
        definition = """
        (foo, 1):
         - a: many nil
         - b: str
        """

        msgs = sendlib.parse(definition)
        foo = msgs[('foo', 1)]

        buf = StringIO()
        writer = foo.writer(buf)
        writer.write('a', [None, None])
        writer.write('b', 'goodbye')

        expected = 'MS\x00\x00\x00\x03fooI\x00\x00\x00\x01L\x00\x00\x00\x02NNS\x00\x00\x00\x07goodbye'
        self.assertEqual(expected, buf.getvalue())

    def test_many_nested_message(self):
        definition = """
        (file, 1):
         - filename: str
         - data: data

        (files, 1):
         - files: many msg (file, 1)
        """

        msgs = sendlib.parse(definition)
        files = msgs[('files', 1)]

        buf = StringIO()
        writer = files.writer(buf)

        sub_files = [msgs.get_message('file')] * 2

        for i, filewriter in enumerate(writer.write('files', sub_files)):
            data = StringIO(str(i))
            filename = 'f%d' % i
            filewriter.write('filename', filename)
            filewriter.write('data', data)

        expected = 'MS\x00\x00\x00\x05filesI\x00\x00\x00\x01L\x00\x00\x00\x02'
        expected += 'MS\x00\x00\x00\x04fileI\x00\x00\x00\x01S\x00\x00\x00\x02f0D\x00\x00\x00\x010'
        expected += 'MS\x00\x00\x00\x04fileI\x00\x00\x00\x01S\x00\x00\x00\x02f1D\x00\x00\x00\x011'

        self.assertEqual(expected, buf.getvalue())



if __name__ == '__main__':
    unittest.main()

