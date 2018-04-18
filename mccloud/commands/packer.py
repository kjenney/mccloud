import click
import json

from mccloud.tools import *
from mccloud.version import VERSION
from mccloud.constants import *

#from .envs import *

config = read_config()
c = Cloudy(config)

@click.group(chain=True)
def packer():
    """Manage and Deploy AMI's with Packer and Ansible

    Examples:

    mccloud packer verbose deploy --env prod

    mccloud packer verbose deploy --env qa

    mccloud packer deploy --env prod

    """
    pass

@packer.command()
def verbose():
    """Turns on verbosity"""
    global c
    c.verbose = True

@packer.command()
@click.option('--ami')
@click.option('--env')
def deploy(ami = None, env = None):
    """This option deploys AMI's with Packer and Ansible"""
    global c
    if not env:
        print('You must pass an environment!')
        exit()
    if not ami:
        c.env = env
        c.assume_role()
        exit()
        c.packer_list()
        ami = click.prompt("Which AMI do you want to deploy? ")
        c.ami = ami
        c.packer_deploy()
