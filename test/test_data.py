import unittest
import sendlib
import string
from StringIO import StringIO

class DataTest(unittest.TestCase):

    definition = """
    (msg, 1):
      - data: data
    (msg, 2):
      - data: data
      - after: str
    """

    def test_write_data(self):
        msgs = sendlib.parse(self.definition)
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

    def test_invalid_instream(self):
        class NoR(object):
            def seek(self): pass
            def tell(self): pass
        class NoS(object):
            def read(self): pass
            def tell(self): pass
        class NoT(object):
            def read(self): pass
            def seek(self): pass

        msgs = sendlib.parse(self.definition)
        msg = msgs[('msg', 1)]

        writer = msg.writer(StringIO())
        self.assertRaises(sendlib.SendlibError, writer.write, 'data', NoR())

    def test_data_read(self):
        msgs = sendlib.parse(self.definition)
        msg = msgs[('msg', 1)]

        din = StringIO('this is some data')
        buf = StringIO()
        writer = msg.writer(buf)
        writer.write('data', din)

        buf.seek(0, 0)
        reader = msg.reader(buf)
        dout = reader.read('data')
        self.assertEqual(dout.read(), 'this is some data')
        self.assertEqual(dout.read(), '')

        buf.seek(0, 0)
        reader = msg.reader(buf)
        dout = reader.read('data')
        self.assertEqual(dout.read(4), 'this')
        self.assertEqual(dout.read(1), ' ')
        self.assertEqual(dout.read(), 'is some data')
        self.assertEqual(dout.read(), '')

    def test_data_readline(self):
        msgs = sendlib.parse(self.definition)
        msg = msgs[('msg', 1)]

        din = StringIO('this is some data')
        buf = StringIO()
        writer = msg.writer(buf)
        writer.write('data', din)

        buf.seek(0, 0)
        reader = msg.reader(buf)
        dout = reader.read('data')
        self.assertEqual(dout.readline(), 'this is some data')
        self.assertEqual(dout.readline(), '')

        din = StringIO('this is some data\nthis is another line')
        buf = StringIO()
        writer = msg.writer(buf)
        writer.write('data', din)

        buf.seek(0, 0)
        reader = msg.reader(buf)
        dout = reader.read('data')
        self.assertEqual(dout.readline(), 'this is some data\n')
        self.assertEqual(dout.readline(), 'this is another line')
        self.assertEqual(dout.readline(), '')

        buf.seek(0, 0)
        reader = msg.reader(buf)
        dout = reader.read('data')
        self.assertEqual(dout.readline(18), 'this is some data\n')
        self.assertEqual(dout.readline(18), 'this is another li')
        self.assertEqual(dout.readline(), 'ne')

    def test_skip(self):
        msgs = sendlib.parse(self.definition)
        msg = msgs[('msg', 2)]

        din = StringIO('this is some data')
        buf = StringIO()
        writer = msg.writer(buf)
        writer.write('data', din)
        writer.write('after', 'foo')

        buf.seek(0, 0)
        reader = msg.reader(buf)
        dout = reader.read('data')
        self.assertEqual(17, dout.bytes_remaining())
        dout.skip()
        self.assertEqual(0, dout.bytes_remaining())
        self.assertEqual('foo', reader.read('after'))

    def test_reallylong(self):
        class LongData(object):
            def __init__(self, length):
                self.length = length
            def read(self, length):
                return '0' * length
            def seek(self, a, b): pass
            def tell(self):
                return self.length

        class NullStream(object):
            def write(self, data): pass

        msgs = sendlib.parse(self.definition)
        msg = msgs[('msg', 1)]

        writer = msg.writer(NullStream())
        writer.write('data', LongData(4294967295))

        writer = msg.writer(NullStream())
        self.assertRaises(sendlib.SendlibError, writer.write, 'data', LongData(4294967296))

if __name__ == '__main__':
    unittest.main()

