import click
import json

from mccloud.tools import *
from mccloud.version import VERSION
from mccloud.constants import *

from mccloud.commands.packer import packer
from mccloud.commands.terraform import terraform
from mccloud.commands.example import example

@click.group()
def entry():
    pass

entry.add_command(packer)
entry.add_command(terraform)
entry.add_command(example)