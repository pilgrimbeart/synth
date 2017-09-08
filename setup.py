#!/usr/bin/env python

from distutils.core import setup

setup(name='synth',
      version='0.1',
      description='An HDL simulator; managing a queue of events and then firing them when they\'re due.',
      url='https://github.com/devicepilot/synth',
      author='DevicePilot',
      author_email='pilgrim.beart@devicepilot.com',
      license='MIT',
      packages=[
            'distutils',
            'distutils.command',
            'requests',
            'zmq',
            'flask',
            'numpy',
            'pytz',
            'flask_cors',
            'zlib',
            'Pillow',
            'boto3'
      ],
      )
