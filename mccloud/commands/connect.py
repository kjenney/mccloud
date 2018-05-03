import click
import json

from mccloud.config import *
from mccloud.cloudy import Cloudy

#from .envs import *

config = read_config()
c = Cloudy(config)

@click.group(chain=True)
def connect():
    """This option let's you connect to an AWS instance

    Examples:

    mccloud connect verbose prod group jump

    mccloud connect verbose prod name hostname

    """
    pass

@connect.command()
def verbose():
    """Turns on verbosity"""
    global c
    c.verbose = True

@connect.command()
def host():
    """Choose a host by group name"""
    global c
    host = click.prompt("Which instance do you want to connect to? ")
    c.host = host
    c.connect()

@connect.command()
def prod():
    """Works on prod environment"""
    global c
    c.env = 'prod'

@connect.command()
def stage():
    """Works on stage environment"""
    global c
    c.env = 'stage'

@connect.command()
def qa():
    """Works on qa environment"""
    global c
    c.env = 'qa'
