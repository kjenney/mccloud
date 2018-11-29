import click
import json

from mccloud.config import *
from mccloud.cloudy import Cloudy

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

    To list all running instances with verbosity under the custom profile:

    mccloud utils verbose instances --env custom

    """
    global c
    if not env:
        c.env = 'base'
    else:
        c.env = env
    c.list_ec2_instances()

@utils.command()
@click.option('--env')
@click.option('--id')
def runningami(env, id):
    """Create an AMI from a running instance

    mccloud utils verbose runningami --env dev --id i-00a6ab899adbfcc2f

    """
    global c
    if not env:
        c.env = 'base'
    else:
        c.env = env
    c.build_ami_from_running_instance(id)

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

@utils.command()
@click.option('--env')
@click.option('--id')
def createinstances(env, id):
    global c
    if not env:
        c.env = 'base'
    else:
        c.env = env
    c.launch_instance_from_ami(id)

@utils.command()
@click.option('--env')
@click.option('--bucket')
@click.option('--string')
def searchs3bucket(env, bucket, string):
    """Search an S3 Bucket for specific files"""
    global c
    if not env:
        c.env = 'base'
    else:
        c.env = env
        if string:
            c.searchs3bucket(bucket, string)
        else:
            print('A search string is required')
