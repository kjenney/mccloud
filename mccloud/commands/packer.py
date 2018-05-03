import click
import json

from mccloud.config import *
from mccloud.cloudy import Cloudy

#from .envs import *

config = read_config()
c = Cloudy(config)

@click.group(chain=True)
def packer():
    """Manage and Deploy AMI's with Packer and Ansible

    Examples:

    mccloud packer verbose deploy --env prod

    mccloud packer verbose deploy --env qa

    mccloud packer first deploy --env dev

    """
    pass

@packer.command()
def verbose():
    """Turns on verbosity"""
    global c
    c.verbose = True

@packer.command()
def first():
    """Set for first-run build of new environments

    Packer assumes that you've got Subnets and Security Groups built
    but if this is your first-run then you would not...so Packer
    can use the default VPC.

    """
    global c
    c.firstrun = True

@packer.command()
@click.option('--ami')
@click.option('--env')
def deploy(ami = None, env = None):
    """Deploys AMI's with Packer and Ansible"""
    global c
    if not env:
        print('You must pass an environment!')
        print('Example:\n\tmccloud packer deploy --env dev --ami dns')
        exit()
    if ami: c.ami = ami
    c.env = env
    c.packer_deploy()
    exit()
