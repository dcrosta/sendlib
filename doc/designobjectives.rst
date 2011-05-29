Design Objectives
=================

``sendlib`` was designed to transmit large messages over streams (i.e.
sockets) without requiring either the client or server end of the connection
to hold the entire message in memory at once. To meet this goal, ``sendlib``
messages must impose some constraints:

- Messages have an explicit schema, essentially a list of (field_name,
  field_type) pairs [1]_
- All fields in a message are required [2]_
- Fields in a message must be read and written in the oder they appear in
  the schema

However, working with ``sendlib`` is not at all draconian, and ``sendlib``
provides a great deal of flexibility in order to meet real world needs. Here
are some of the features of ``sendlib``:

- Native support for ``int``, ``str``, ``unicode``, ``bool``, ``None``, and
  file objects
- Support for nesting messages within other messages, to create flexible
  schemas that are easy to read
- Low message size overhead for a general-purpose serialization library
- Low memory footprint

.. rubric:: Notes

.. [1] Any given field may have multiple allowed types; however in a given
       serialized message, each field will have a single, specific type
.. [2] There is a special type, ``nil``, which can be used to make a field
       "optional". See [REF] for more details.

