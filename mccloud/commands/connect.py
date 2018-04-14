import click
import json

from mccloud.tools import *
from mccloud.version import VERSION
from mccloud.constants import *

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

@packer.command()
def verbose():
    """Turns on verbosity"""
    global c
    c.verbose = True

@packer.command()
def hostname():
    """Choose a host by group name"""
    global c
    hostname = click.prompt("Which instance do you want to connect to? ")
    c.hostname = hostname
    c.connect()

@packer.command()
def prod():
    """Works on prod environment"""
    global c
    c.env = 'prod'

@packer.command()
def stage():
    """Works on stage environment"""
    global c
    c.env = 'stage'

@packer.command()
def qa():
    """Works on qa environment"""
    global c
    c.env = 'qa'