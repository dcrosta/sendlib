Tutorial by Example
===================

Message Schemas
---------------

``sendlib`` message schemas are a line-oriented, plain-text format,
beginning with a message declaration (a ``(name, version)`` pair), followed
by zero or more [1]_ field declarations.

::

    (auth, 1):
     - username: str
     - password: str

    (authreply, 1):
     - success: bool
     - message: str or nil

White space is generally ignored, and line content after a hash mark
(``#``) are considered comments, and ignored by the parser. Thus, this
schema is equivalent to the above:

::

    ( auth , 1 ) :
     -       username:     str
     -password:str

    # gonna have a few blank lines here



    (authreply, 1)     :
     - success: bool
     - message:         str     or nil

However, whitespace is important within tokens (message or field names, and
type names). None of the following message schemas will be equivalent to the
above definition, or, in fact, to each other:

::

   (auth, 1):
    - username: str
    - password: str or n i l  # this will be a parse error, since
                              # "n" is not a valid field type

   (au th, 1): # message name will be "au th"
    - username: str
    - password: str or nil

   (auth, 1):
    - user name: str # field name will be "user name"
    - password: str or nil


Writing Messages
----------------

Suppose we have the message schema from above, defined in a file named
"``my.schema``":

::

    (auth, 1):
    - username: str
    - password: str


We can parse the schema, obtain a reference to a :class:`~sendlib.Message`,
and then to a :class:`~sendlib.Writer`, and use this to write to our stream:

::

    registry = sendlib.parse(file("my.schema"))
    auth_message = registry.get_message("auth")
    auth_writer = auth_message.writer(sys.stdout) # or any stream

    auth_writer.write("username", "my_username")
    auth_writer.write("password", "my_password")
    auth_writer.flush()

For some streams, calling :meth:`~sendlib.Writer.flush` may not be
necessary, but it is always safe to include it.


Reading Messages
----------------

Reading looks very similar to writing:

::

    registry = sendlib.parse(file("my.schema"))
    auth_message = registry.get_message("auth")
    auth_reader = auth_message.reader(sys.stdin) # or any stream

    username = auth_writer.read("username")
    password = auth_writer.read("password")


.. rubric:: Notes

.. [1] That's right, zero or more. Sine a message is identified by its name,
       in many cases, it may not need any additional fields, for instance, a
       logout message.
