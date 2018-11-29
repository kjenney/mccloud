import click
import json

from mccloud.config import *
from mccloud.cloudy import Cloudy

#from .envs import *

config = read_config()
c = Cloudy(config)

@click.group(chain=True)
def ansible():
    """Provision EC2 instances with Ansible

    Examples:

    mccloud ansible verbose deploy --env prod

    mccloud ansible verbose deploy --env qa

    mccloud ansible deploy --env dev

    """
    pass

@ansible.command()
def verbose():
    """Turns on verbosity"""
    global c
    c.verbose = True

@ansible.command()
@click.option('--ami')
@click.option('--env')
def deploy(ami = None, env = None):
    """Deploy EC2 instances from an AMI with Ansible"""
    global c
    if not env:
        print('You must pass an environment!')
        print('Example:\n\tmccloud ansible deploy --env dev --ami dns')
        exit()
    if ami: c.ami = ami
    c.env = env
    c.ansible_deploy()
    exit()
