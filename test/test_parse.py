# -*- coding: utf-8 -*-

import os
import string
from StringIO import StringIO
import unittest

import sendlib

class ParserTest(unittest.TestCase):

    def test_file_like(self):
        schema = """
        (foo, 1):
        - a: int
        """
        sendlib.parse(StringIO(schema))

    def test_no_fields(self):
        definition = """
        (foo, 1):
        """

        registry = sendlib.parse(definition)
        self.assertEqual(1, len(registry.messages))

        expected = sendlib.Message(registry, 'foo', 1, ())
        actual = registry[('foo', 1)]
        self.assertEqual(expected.name, actual.name)
        self.assertEqual(expected.version, actual.version)
        self.assertEqual(expected.fields, actual.fields)

    def test_registry(self):
        definition = """
        (foo, 1):
         - a: str
        """

        registry = sendlib.parse(definition)
        self.assertTrue(bool(registry[('foo', 1)]))
        self.assertRaises(KeyError, lambda: registry[('FOO', 1)])

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

    def test_nested_message(self):
        definition = """
        (foo, 1):
         - bar: str
         - baz: str

        (baz, 1):
         - foo: msg (foo, 1)
        """
        registry = sendlib.parse(definition)

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

    def test_nested_message_or_nil(self):
        definition = """
        (foo, 1):
         - a: str
         - b: str

        (bar, 1):
         - m: msg(foo, 1) or nil
        """
        registry = sendlib.parse(definition)

    def test_unknown_nested_message(self):
        definition = """
        (foo, 1):
         - a: str
         - b: str

        (bar, 1):
         - m: msg (FOO, 1)
        """
        self.assertRaises(sendlib.ParseError, sendlib.parse, definition)

    def test_orphan_field(self):
        definition = """
         - a: str
        (foo, 1):
         - b: str
        """
        self.assertRaises(sendlib.ParseError, sendlib.parse, definition)

    def test_many(self):
        definition = """
        (foo, 1):
         - a: many str
         - b: str
        """

        msgs = sendlib.parse(definition)
        foo = msgs[('foo', 1)]

    def test_parse_comments(self):
        definition = """
        (foo, 1): # comment after the message declaration
         - username: str#immediate comment
        # line comment
        """

        sendlib.parse(definition)

    def test_parse_spaces(self):
        definition = """
        (f o o, 1):
         - ba r: str
        """

        msgs = sendlib.parse(definition)
        self.assertNotEqual(None, msgs.get_message('f o o'))

        foo = msgs.get_message('f o o')
        self.assertEqual('ba r', foo.fields[0].name)

if __name__ == '__main__':
    unittest.main()

