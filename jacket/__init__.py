"""
:mod:`jacket` -- Cloud IaaS Platform
===================================

.. automodule:: jacket
   :platform: Unix
   :synopsis: Infrastructure-as-a-Service Cloud platform.
"""

import os

os.environ['EVENTLET_NO_GREENDNS'] = 'yes'

import eventlet
