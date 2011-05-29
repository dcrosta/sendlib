``sendlib`` API Documentation
=============================

Getting Messages
----------------

.. automodule:: sendlib
   :members: parse

.. autoclass:: MessageRegistry
   :members:

   .. automethod:: __getitem__

.. autoclass:: Message
   :members:

.. autoclass:: Field


Reading and Writing Streams
---------------------------

.. autoclass:: Reader
   :members:

.. autoclass:: Writer
   :members:

.. autoclass:: Data
   :members: read, readline, skip, bytes_remaining


Exceptions
----------

.. autoexception:: ParseError

   Raised when :func:`parse` cannot successfully parse the schema

.. autoexception:: SendlibError

   Raised at runtime if an error occurs reading or writing the stream

