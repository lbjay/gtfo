#!/usr/bin/env 

import sys, os
abspath = os.path.dirname(__file__)
sys.path.append(abspath)
os.chdir(abspath)

import logging
from www import application

logging.basicConfig(filename='static/www.txt', level=logging.DEBUG,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
