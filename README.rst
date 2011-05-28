``sendlib``
===========

``sendlib`` is a lightweight library for serializing messages, usually to be
sent over a socket, pipe, or other stream. Sendlib is specialized for
sending messages which are read serially, unlike other serialization formats
often used (like JSON_, YAML_, or XML_).

.. _JSON: http://json.org/
.. _YAML: http://yaml.org/
.. _XML: http://www.w3.org/standards/xml/


Design Objectives
-----------------

``sendlib`` was designed to transmit large messages over streams (i.e.
sockets) without requiring either the client or server end of the connection
to hold the entire message in memory at once. To meet this goal, ``sendlib``
messages:

- Are composed of fields
- Are explicitly defined
- Require that all fields be present
- Require that all fields appear in a consistent order, even when optional

``sendlib`` supports the following data types: ``str`` (or ``unicode``),
``int`` (or ``long``), ``float``, ``bool``, and ``data``, which can be used
to store contents of file-like objects. Fields within messages can be made
optional using the special data type ``nil``. ``sendlib`` makes no attempt
to serialize custom objects or any "advanced" Python data types. These can
be serialized by breaking them down into component fields.

``sendlib`` serializes fields in the order they are listed in the message
defintion, and each field, even if optional, is serialized in the message.
Field names are not serialized in the message, but are used in the API to
provide more helpful feedback in exceptions, and to allow better validation
and error checking.


Example Usage
-------------

Before ``sendlib`` can manipulate messages, you must define them. Message
definitions are simple, YAML-like structures, like the following simple
example:

::

  (login, 1):
    - username: str
    - passhash: str
    - passsalt: str

This defines a message, named ``login`` with version ``1``, composed of
three required fields, ``username``, ``passhash``, and ``passsalt``. You
might then send such a message like:

::

  messages = sendlib.parse(file('messages').read())
  login_message = messages[('login', 1)]

  writer = login_message.writer(a_stream)
  writer.send('username', username)
  writer.send('passhash', password_hash)
  writer.send('passsalt', password_salt)

Your server code on the receiving end would then read a message similarly:

::

  messages = sendlib.parse(file('messages').read())
  login_message = messages[('login', 1)]

  reader = login_message.reader(a_stream)
  username = reader.send('username')
  password_hash = reader.send('passhash')
  password_salt = reader.send('passsalt')


Serialization Format
--------------------

``str``
  "``S``" + *length, 4-byte big-endian integer* + *UTF-8 string*

``int``
  "``I``" + *4-byte big-endian integer*

``float``
  "``F``" + *8-bute big-endian float*

``bool``
  "``B``" + "``t``" or "``f``"

``data``
  "``D``" + *4-byte length* + *raw data bytes*

``nil``
  "``N``"

Messages are identified by a message header, consisting of a literal "``M``"
followed by a serialized ``str`` (the message name) and a serialized ``int``
(the message version).



License and Credits
-------------------

Copyright (c) 2011, Daniel Crosta <dcrosta@late.am>.
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

