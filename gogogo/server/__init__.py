import os, json

import bottle
from bottle import Bottle

from gogogo.game import Game, GameError
from gogogo.server.app import app, routes

def run(addr='localhost', port=9090, **kwargs):
    bottle.debug(kwargs.pop('debug', False))
    app.config.update(media_root=kwargs.pop('media',
                                            os.path.join(os.getcwd(), 'media', 'web')))
    bottle.run(app=app, host=addr, port=port,
               **dict({'reloader': kwargs.pop('reload', False), 
                       'interval': kwargs.pop('reload_interval', 1)},
                      **kwargs))
