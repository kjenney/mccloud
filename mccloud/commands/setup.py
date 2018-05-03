import click
import json

from mccloud.config import *
from mccloud.cloudy import Cloudy

config = read_config()
c = Cloudy(config)

click.group()

@click.group(chain=True)
def setup():
    """This option grabs all of the required tools that aren't on Pip

    Example:

    mccloud setup tools

    """
    pass

@setup.command()
def tools():
    global c
    c.install_tools()
