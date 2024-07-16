import importlib

from .actorpoint import get_actorpoint
from .awesomefilm import get_awesomefilm
from .dailyscript import get_dailyscript
from .imsdb import get_imsdb
from .screenplays import get_screenplays
from .scriptpdf import get_scriptpdf
from .scriptsavant import get_scriptsavant
from .scriptslug import get_scriptslug
from .sfy import get_sfy
from .utilities import *
from .weeklyscript import get_weeklyscript


def get_download_from_url_func(source):
    module = importlib.import_module(f"sources.{source}")
    return getattr(module, "get_script_from_url")


def get_scripts(source, metadata_only):
    if source == "imsdb":
        get_imsdb(metadata_only)
    elif source == "screenplays":
        get_screenplays(metadata_only)
    elif source == "scriptsavant":
        get_scriptsavant(metadata_only)
    elif source == "weeklyscript":
        get_weeklyscript(metadata_only)
    elif source == "dailyscript":
        get_dailyscript(metadata_only)
    elif source == "awesomefilm":
        get_awesomefilm(metadata_only)
    elif source == "sfy":
        get_sfy()
    elif source == "scriptslug":
        get_scriptslug(metadata_only)
    elif source == "actorpoint":
        get_actorpoint(metadata_only)
    elif source == "scriptpdf":
        get_scriptpdf(metadata_only)
    else:
        print("Invalid source.")
