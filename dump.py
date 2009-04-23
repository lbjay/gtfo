#!/usr/bin/env python

import os
import rdflib

root = '/home/ed/bzr/c4libbers'
store = "%s/store" % root
dump = "%s/static/dump.rdf" % root
tmp = "%s.tmp" % dump

g = rdflib.ConjunctiveGraph('Sleepycat')

try:
    g.open(store)
    g.serialize(file(tmp, 'w'))
    os.rename(tmp, dump)
except Exception, e:
    print e
finally:
    g.close()
