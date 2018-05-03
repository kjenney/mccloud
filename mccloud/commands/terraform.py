import click
import json

from mccloud.config import *
from mccloud.cloudy import Cloudy

config = read_config()
c = Cloudy(config)

@click.group(chain=True)
def terraform():
    """Do stuff with Terraform

    Examples:

    mccloud terraform verbose deploy --env prod

    mccloud terraform verbose destroy --env prod

    mccloud terraform deploy --env prod

    """
    pass

@terraform.command()
def verbose():
    """Turns on verbosity"""
    global c
    c.verbose = True

@terraform.command()
@click.option('--env')
def deploy(env):
    """This option deploys to AWS using Terraform"""
    global c
    c.env = env
    c.terraform_deploy()

@terraform.command()
@click.option('--env')
def destroy(env):
    """This option destroys using Terraform"""
    global c
    c.env = env
    c.terraform_destroy()
