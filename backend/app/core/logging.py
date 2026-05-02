from logging.config import dictConfig

def configure_logging() -> None:
    dictConfig({
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "rich" : {
                "format": "%(asctime)s | %(levelname)s | %(name)s | %(message)s"
            }
        },
        "handlers" : {
            "console" : {
                "class" : "rich.logging.RichHandler",
                "level" : "INFO",
                "formatter" : "rich",
                "rich_tracebacks" : True,
                "markup" : True,
            },
        },
        "loggers" : {
            "app" : {
                "handlers" : ["console"],
                "level" : "INFO",
                "propagate" : False,
            },
            "uvicorn" : {
                "handlers" : ["console"],
                "level" : "INFO",
                "propagate" : False,
            },
            "uvicorn.error" : {
                "handlers" : ["console"],
                "level" : "INFO",
                "propagate" : False,
            },
            "uvicorn.access" : {
                "handlers" : ["console"],
                "level" : "INFO",
                "propagate" : False,
            },
        },
        "root" : {
            "handlers" : ["console"],
            "level" : "WARNING",
        },
    })