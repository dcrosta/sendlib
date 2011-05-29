``sendlib``
===========

``sendlib`` is a lightweight library for serializing messages, usually to be
sent over a socket, pipe, or other stream. Sendlib is specialized for
sending messages which are read serially, unlike other serialization formats
often used (like JSON_, YAML_, or XML_).

.. _JSON: http://json.org/
.. _YAML: http://yaml.org/
.. _XML: http://www.w3.org/standards/xml/

Why not JSON, YAML, or XML? ``sendlib`` natively supports reading messages
one piece at a time, to keep memory footprint small, and has native support
for sending and receiving file-like objects with the ``data`` type.

If your application needs to send and receive large data blobs, especially
if your application can process that data without random access, ``sendlib``
may be a good fit to reduce memory usage. On the other hand, if you need
random access to fields within your message, have small messages, or have
messages with, or complex nesting structures, then ``sendlib`` may not be
for you.


Contents
--------
.. toctree::
   :maxdepth: 2

   designobjectives
   tutorial
   api

