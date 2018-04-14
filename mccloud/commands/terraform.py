import click
import json

from mccloud.tools import *
from mccloud.version import VERSION
from mccloud.constants import *

config = read_config()
c = Cloudy(config)

@click.group(chain=True)
def terraform():
    """Do stuff with Terraform
    
    Examples:

    mccloud terraform verbose prod deploy

    mccloud terraform verbose prod destroy

    mccloud terraform prod deploy
    
    """
    pass

@terraform.command()
def verbose():
    """Turns on verbosity"""
    global c
    c.verbose = True

@terraform.command()
def deploy():
    """This option deploys to AWS using Terraform"""
    global c
    c.terraform_deploy()

@terraform.command()
def destroy():
    """This option destroys using Terraform"""
    c.terraform_destroy()

@terraform.command()
def prod():
    """Works on prod environment"""
    global c
    c.env = 'prod'

@terraform.command()
def stage():
    """Works on stage environment"""
    global c
    c.env = 'stage'

@terraform.command()
def qa():
    """Works on qa environment"""
    global c
    c.env = 'qa'