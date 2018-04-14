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

    mccloud packer verbose prod deploy

    mccloud packer verbose prod destroy

    mccloud packer prod deploy
    
    """
    pass

@packer.command()
def verbose():
    """Turns on verbosity"""
    global c
    c.verbose = True

@packer.command()
#@click.option('--ami', prompt=True)
def deploy():
    """This option deploys to AWS using Terraform"""
    global c
    c.packer_list()
    ami = click.prompt("Which AMI do you want to deploy? ")
    c.ami = ami
    c.packer_deploy()

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