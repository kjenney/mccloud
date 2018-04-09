import click
import json

from mccloud.tools import *
from mccloud.version import VERSION
from mccloud.constants import *

config = read_config()

@click.group()
@click.option('--verbose', is_flag=True)
@click.option('--env',
              help='This is the Terraform environment to grab the inventory from.', default='none')
@click.option('--config', default=config)
@click.pass_context
def main(ctx, verbose, env, config):
    if config:
      ctx.obj['CONFIG'] = config
      iacpath = ctx.obj['CONFIG']['IACPATH']
      if verbose:
          ctx.obj['VERBOSE'] = True
          click.echo('------- We are in verbose mode -------\n')
      else:
          ctx.obj['VERBOSE'] = False
      if env:
          c = Cloudy(config, env, ctx.obj['VERBOSE'])
          if c.verify_env():
              ctx.obj['ENV'] = env
          else:
              print('Invalid Environment')
              exit()
      ctx.obj['CLOUD'] = c
    else:
      click.echo('Config file required!!!')
      exit()

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
    c = ctx.obj['CLOUD']
    if destroy:
      click.echo('------- Destroying with Terraform -------\n')
      c.terraform_destroy()
    else:
      click.echo('------- Deploying with Terraform -------\n')
      c.terraform_deploy()

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
@click.pass_context
def setup(ctx):
    """This option grabs all of the required tools that aren't on Pip"""
    ctx.obj['CLOUD'].install_tools()

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
