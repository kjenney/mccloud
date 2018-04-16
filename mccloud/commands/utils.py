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