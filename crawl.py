#!/usr/bin/env python

import logging
import time
from datetime import datetime

import pydot
import rdflib
from settings import *
from namespaces import *

pause_between_crawls = 60 * 15 # seconds

g = rdflib.ConjunctiveGraph('Sleepycat')
g.open('store', create=True)

def crawl(uri, runtime):
    # only load a uri once per crawl call 
    if already_seen(uri, runtime):
        return

    # grab the rdf at the URI
    try:
        context = parse(uri)
        add_crawled(uri, runtime)

        # if we found an attendee crawl their friends
        if is_attendee(uri):
            # load any external interests
            load_interests(uri)
            logging.info("found attendee %s" % name(uri))
            for friend in  g.objects(subject=uri, predicate=foaf.knows):
                crawl(friend, runtime)

        # otherwise forget about whoever it is 
        else:
            logging.info("not an attendee: " + uri)
            context.remove((None, None, None))

    except Exception, e: 
        logging.error(e)

def already_seen(uri, runtime):
    last_crawl = last_crawled(uri)
    if str(last_crawl) == str(runtime):
        return True
    return False

def is_attendee(uri):
    return (uri, swc.attendeeAt, EVENT_URI) in g

def attendees():
    attendees = []
    for uri in g.subjects(swc.attendeeAt, EVENT_URI):
        attendees.append({'uri': uri, 
                          'name': name(uri), 
                          'homepage': homepage(uri),
                          'blog': blog(uri),
                          'interests': interests(uri),
                          'based_near': based_near(uri),
                          'picture': picture(uri),
                          'nick': nick(uri),
                          'twitter': account(uri, 'twitter.com'),
                          'identica': account(uri, 'identi.ca'),
                          'lastfm': account(uri, 'last.fm'),
                          'flickr': account(uri, 'flickr.com'),
                          'friendfeed': account(uri, 'friendfeed.com'),
                          'facebook': account(uri, 'facebook.com'),
                          'delicious': account(uri, 'delicious.com'),
                          'enjoysthings': account(uri, 'enjoysthin.gs'),
                          'publications': publications(uri),
                          })
    attendees.sort(lambda a, b: cmp(a['name'], b['name']))
    return attendees

def attendees_graph():
    q = """
        SELECT ?s ?p ?o WHERE { ?s <%s> <%s> .  ?s ?p ?o .  }
        """
    sg = rdflib.ConjunctiveGraph()
    sg += g.query(q % (swc.attendeeAt, EVENT_URI))
    set_prefixes(sg)
    return sg

def set_prefixes(graph):
    graph.bind('owl', owl)
    graph.bind('bio', bio)
    graph.bind('rel', rel)
    graph.bind('psych', psych)
    graph.bind('post', post)
    graph.bind('cc', cc)
    graph.bind('xhtml', xhtml)
    graph.bind('wot', wot)
    graph.bind('pim', pim)
    graph.bind('dce', dce)
    graph.bind('geo', geo)
    graph.bind('swc', swc) 
    graph.bind('foaf', foaf)
    graph.bind('dcterms', dcterms)
    graph.bind('xsd', xsd)

def name(uri):
    for o in g.objects(uri, foaf.name):
        return unicode(o)
    return None

def nick(uri):
    return first_object(uri, foaf.nick)

def picture(uri):
    return first_object(uri, foaf.depiction) or first_object(uri, foaf.img)

def homepage(uri):
    return first_object(uri, foaf.homepage)

def blog(uri):
    return first_object(uri, foaf.weblog)

def first_object(s, p):
    for o in g.objects(s, p):
        return o
    return None

def account(uri, domain):
    for  o in g.objects(uri, foaf.holdsAccount):
        if domain in o:
            return o

def publications(uri):
    return first_object(uri, foaf.publications)

def based_near(uri):
    nsmap = {'geo':geo, 'foaf':foaf}
    vars = {'?attendee': uri}
    query = """
            SELECT ?name ?lat ?long
            WHERE {
                ?attendee foaf:based_near ?place .  
                ?place a geo:SpatialThing . 
                ?place foaf:name ?name .
                ?place geo:lat ?lat . 
                ?place geo:long ?long }
            """
    for (name, lat, long) in g.query(query, initNs=nsmap, initBindings=vars):
        return {'name':name, 'lat':lat, 'long':long} # just return one
    return None

def load_interests(uri):
    for o in g.objects(uri, foaf.interest):
        if o not in g.subjects():
            logging.info("loading interest %s" % o)
            context = parse(o)
            if not context:
                logging.error("unable to load interest %s" % o)

def interests(uri):
    i = []
    for o in g.objects(uri, foaf.interest):
        labels = []
        for l in g.objects(o, rdflib.RDFS.label):
            # give preference to labels w/ no language or English ones
            if not l.language or l.language == 'en':
                labels.append({'label': l, 'uri': o})
        for name in g.objects(o, rdflib.URIRef('http://rdf.freebase.com/ns/type.object.name')):
            labels.append({'label': name, 'uri': o})
            break
        i = i + labels
    return i

def last_crawled(uri):
    for o in g.objects(uri, dcterms.modified):
        return o
    return None

def add_crawled(uri, runtime):
    g.remove((uri, dcterms.modified, None))
    g.add((uri, dcterms.modified, runtime))

def get_runtime():
    n = datetime.now()
    return rdflib.Literal(n.strftime('%Y-%m-%dT%H:%M:%S'), 
                          datatype=xsd.dateTime)

def dot():
    subgraph = attendees_graph()
    dot = pydot.Dot()
    for s, o in subgraph.subject_objects(predicate=foaf.knows):
        l1 = name(s)
        l2 = name(o)
        logging.info(str(l1) + " knows " + str(l2))
        if not l1 or not l2:
            continue

        n1 = pydot.Node(l1.encode('ascii', 'ignore'))
        dot.add_node(n1)
        
        n2 = pydot.Node(l2.encode('ascii', 'ignore'))
        dot.add_node(n2)

        dot.add_edge(pydot.Edge(n1, n2))

    return dot

def size():
    return len(g)

def parse(uri):
    context = None
    try:
        logging.info("parsing %s" % uri)
        context = g.parse(uri)
    except Exception, e:
        logging.error(e)
        logging.debug("trying rdfa extractor on %s" % uri)
        u = "http://www.w3.org/2007/08/pyRdfa/extract?space-preserve=true&uri=" + uri
        context = g.parse(u, identifier=uri)
    if not context:
        logging.error("unable to extract triples from %s" % uri)
    return context

if __name__ == '__main__':
    logging.basicConfig(filename='static/crawls.txt', level=logging.DEBUG,
            format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")

    try:
        while True:
            logging.info("starting another crawl")
            crawl(SEED_URI, get_runtime())
            logging.info("sleeping for %i seconds" % pause_between_crawls)
            time.sleep(pause_between_crawls)
    except Exception, e:
        logging.error(e)
    finally:
        logging.info('crawler shutting down')
        g.close()
