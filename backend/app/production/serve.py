"""One controlled worker; real peer preserved; no request/exception payload logs."""
import logging
import sys
import uvicorn


class SafeFormatter(logging.Formatter):
    def format(self,record):
        # Do not format third-party messages/args/tracebacks containing secrets.
        return 'Merge runtime: '+('error; details suppressed' if record.levelno>=logging.ERROR else 'lifecycle event')


LOGGING={'version':1,'disable_existing_loggers':False,
    'formatters':{'safe':{'()':SafeFormatter}},
    'handlers':{'safe':{'class':'logging.StreamHandler','formatter':'safe','stream':'ext://sys.stderr'}},
    'root':{'handlers':['safe'],'level':'WARNING'},
    'loggers':{'uvicorn':{'handlers':['safe'],'level':'INFO','propagate':False},
        'uvicorn.error':{'handlers':['safe'],'level':'INFO','propagate':False},
        'uvicorn.access':{'handlers':[],'propagate':False,'level':'CRITICAL'},
        'sqlalchemy.engine':{'handlers':[],'propagate':False,'level':'CRITICAL'}}}


def main():
    if len(sys.argv)!=1:raise SystemExit('Production server accepts no overrides')
    try:
        uvicorn.run('app.production.application:create_production_app',factory=True,host='0.0.0.0',port=8000,
            workers=1,proxy_headers=False,forwarded_allow_ips='',access_log=False,log_config=LOGGING,
            timeout_graceful_shutdown=20,timeout_keep_alive=5,limit_concurrency=256)
    except Exception:raise SystemExit('Production startup failed; private details suppressed') from None


if __name__=='__main__':main()
