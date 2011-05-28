# -*- coding: utf-8 -*-

import os
import string
from StringIO import StringIO
import unittest

import sendlib

class ParserTest(unittest.TestCase):

    def test_no_fields(self):
       definition = """
       (foo, 1):
       """

       msgs = sendlib.parse(definition)
       self.assertEqual(1, len(msgs))

       expected = sendlib.Message('foo', 1, [])
       actual = msgs[('foo', 1)]
       self.assertEqual(expected.name, actual.name)
       self.assertEqual(expected.version, actual.version)
       self.assertEqual(expected.fields, actual.fields)

    def test_field_types(self):
        definition = """
        (foo, 1):
          - i: int
          - in: int or nil
          - s: str
          - sn: str or nil
          - f: float
          - fn: float or nil
          - b: bool
          - bn: bool or nil
          - d: data
          - dn: data or nil
          - n: nil
          - sifbdn: str or int or float or bool or data or nil
        """

        msgs = sendlib.parse(definition)
        msg = msgs[('foo', 1)]

        # spot-check fields
        self.assertEqual(msg.fields[0].types, ('int', ))
        self.assertEqual(msg.fields[3].types, ('str', 'nil'))
        self.assertEqual(msg.fields[-1].types, ('str', 'int', 'float', 'bool', 'data', 'nil'))

        definition = """
        (foo, 1):
         - broken: not_a_type
        """
        self.assertRaises(sendlib.ParseError, sendlib.parse, definition)

    def test_duplicates(self):
        definition = """
        (foo, 1):
         - i: int

        (foo, 1):
         - i: int
        """
        self.assertRaises(sendlib.ParseError, sendlib.parse, definition)

        definition = """
        (foo, 1):
         - i: int

        (foo, 2):
         - i: int
        """
        # should not raise
        sendlib.parse(definition)

        definition = """
        (foo, 1):
         - a: int
         - b: str
         - a: int
        """
        self.assertRaises(sendlib.ParseError, sendlib.parse, definition)


if __name__ == '__main__':
    unittest.main()

