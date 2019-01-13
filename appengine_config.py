from google.appengine.ext.appstats import recording

appstats_CALC_RPC_COSTS = False
appstats_SHELL_OK = True
#remoteapi_CUSTOM_ENVIRONMENT_AUTHENTICATION = ('HTTP_X_APPENGINE_INBOUND_APPID',['wokantest'])

def webapp_add_wsgi_middleware(app):
    app = recording.appstats_wsgi_middleware(app)
    return app