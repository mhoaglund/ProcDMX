#!/usr/bin/env python

"""
Setup.py for multitrackstereo module
"""

from distutils.core import setup, Extension

multitrackstereo_module = Extension('_multitrackstereo', sources=['multitrack_wrap.cxx','multitrackstereo.cpp'])

setup (
    name = 'multitrackstereo',
    author = 'mhoaglund',
    description = 'stereo vision handler with gpu acceleration',
    ext_modules = [multitrackstereo_module],
    py_modules = ['multitrackstereo']
    )
