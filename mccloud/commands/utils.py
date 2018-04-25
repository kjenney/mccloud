import click
import json

from mccloud.tools import *
from mccloud.version import VERSION
from mccloud.constants import *

config = read_config()
c = Cloudy(config)

@click.group(chain=True)
def utils():
    """Various commands to interact with AWS

    Examples:

    mccloud utils base

    """
    pass

@utils.command()
def verbose():
    """Turns on verbosity"""
    global c
    c.verbose = True

@utils.command()
@click.option('--region')
def base(region):
    """Create a base image off of Centos 7

    Defaults to us-east-1

    mccloud utils base --region us-west-1

    """
    global c
    if region:
        c.create_base_image(region)
    else:
        c.create_base_image('us-east-1')

@utils.command()
@click.option('--env')
def instances(env):
    """List EC2 instances

    Pass verbose:

    To list all instances with verbosity under the custom profile:

    mccloud utils verbose listec2 --env custom

    """
    global c
    if not env:
        c.env = 'base'
    else:
        c.env = env
    c.list_ec2()

@utils.command()
def envs():
    """List Environments

    To list all environments

    mccloud utils listenvs

    """
    global c
    c.list_envs()

@utils.command()
def keys():
    """Generate SSH Keys for config.json

    mccloud utils keys

    """
    global c
    c.generate_ssh_keys()
