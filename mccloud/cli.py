import click
import json

from mccloud.tools import *
from mccloud.version import VERSION
import mccloud.constants

@click.group()
@click.option('--verbose', is_flag=True)
@click.option('--env',
              help='This is the Terraform environment to grab the inventory from.')
@click.pass_context
def main(ctx, verbose, env):
    if verbose:
        ctx.obj['VERBOSE'] = verbose
        click.echo('We are in verbose mode')
    if env:
        ctx.obj['ENV'] = env

@main.command()
@click.pass_context
@click.option('--playbook',
              help='This is the playbook you want to use.')
@click.option('--host',
              help='The host you want to run a command on.')
@click.option('--cmd',
              help='The command you want to run.')
def ansible(ctx, playbook, host, cmd):
    """Use Ansible to deploy to or run a command on a server"""
    env = ctx.obj['ENV']

    if playbook:
      print('Deploying to Ansible')
      ansible_deploy(env, playbook)
    else:
      ansible_command(env, host, cmd)


@main.command()
@click.pass_context
@click.option('--destroy', is_flag=True)
def terraform(ctx, destroy):
    """This option provisions resources using Terraform"""
    env = ctx.obj['ENV']

    if destroy:
      print('Destroying with Terraform')
      terraform_destroy(env)
    else:
      print('Deploying to Terraform')
      terraform_deploy(env)

@main.command()
@click.pass_context
def packer(ctx):
    """This option provisions AMI images with Packer and Ansible"""
    env = ctx.obj['ENV']

    if env is None:
      print("Environment is required")
      exit()
    packer_deploy(env)


@main.command()
def setup():
    """This option grabs all of the required tools that aren't on Pip"""
    install_tools(mccloud.constants.BINPATH)

@main.command()
@click.option('--dir',
              help='This is the name of the project directory')
def scaffold(dir):
    """This option builds the scaffolding for a new project"""
    build_scaffold(dir)

@main.command()
def version():
    print('version: ' + VERSION)

def entry():
    return main(obj={})
