#!/usr/bin/env python

import random
import atexit

import web
import rdflib

import crawl
import settings

urls = (
        '/attendees$',          'Attendees',
        '/attendees.rdf$',      'AttendeesRdf',
        '/attendees.png$',      'AttendeesPng',
        '/attendees.ps$',       'AttendeesPostscript',
        '/attendees.svg$',      'AttendeesSvg',
        '/attendees/rnd$',      'RandomAttendee',
)

render = web.template.render('templates', cache=False)

class Attendees:

    def GET(self):
        return render.attendees(settings, crawl.attendees())


class AttendeesRdf:

    def GET(self):
        ag = crawl.attendees_graph()
        web.header("Content-type", "application/rdf+xml")
        return ag.serialize()


class AttendeesPng:

    def GET(self):
        dot = crawl.dot()
        web.header('Content-type', 'image/png')
        return dot.create_png()


class AttendeesPostscript:

    def GET(self):
        dot = crawl.dot()
        web.header('Content-type', 'application/postscript')
        return dot.create_ps()


class AttendeesSvg:

    def GET(self):
        dot = crawl.dot()
        web.header('Content-type', 'image/svg+xml')
        return dot.create_svg()


class RandomAttendee:

    def GET(self):
        # pick a random attendee
        folks = crawl.attendees()
        person = folks[random.randint(0, len(folks)-1)]
        return render.random_attendee(settings, person)


application = web.application(urls, globals()).wsgifunc()
atexit.register(lambda: crawl.g.close())

if __name__ == '__main__':
    app = web.application(urls, globals())
    app.run()
    application.run()
