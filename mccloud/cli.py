import click
import json

from mccloud.config import *
from mccloud.cloudy import Cloudy
from mccloud.version import VERSION
from mccloud.constants import *

from mccloud.commands.packer import packer
from mccloud.commands.ansible import ansible
from mccloud.commands.terraform import terraform
from mccloud.commands.connect import connect
from mccloud.commands.utils import utils
from mccloud.commands.setup import setup

@click.group()
def entry():
    pass

@entry.command()
def version():
    """Show the version"""
    print('version: ' + VERSION)

entry.add_command(packer)
entry.add_command(ansible)
entry.add_command(terraform)
entry.add_command(connect)
entry.add_command(utils)
entry.add_command(setup)
entry.add_command(version)
