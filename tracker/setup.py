#!/usr/bin/env python

"""
Setup.py for multitrackstereo module
"""

from distutils.core import setup, Extension

multitrackstereo_module = Extension(
    '_MultiTrack', 
    sources=['multitrack_wrap.cxx','multitrackstereo.cpp'],
    swig_opts=['-c++'],
    library_dirs=['/usr/include/opencv2'],
    libraries=['opencv_core','opencv_highgui','opencv_imgproc','opencv_gpu', 'opencv_video']
    )

setup (
    name = 'multitrackstereo',
    author = 'mhoaglund',
    description = 'stereo vision handler with gpu acceleration',
    ext_modules = [multitrackstereo_module],
    headers = ['multitrackstereo.h'],
    py_modules = ['multitrackstereo']
    )
