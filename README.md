# mccloud

A tool to administer AWS...

Uses Terraform, Ansible, and a host of other tools to make life easier.

Config is pulled from config.json in the working directory. Here's a sample config file:

{
  "BINPATH": "/mystuff/.env/bin",
  "ANSIBLEPATH": "/mystuff/ansible-repo",
  "IACPATH": "/mystuff/iac_example",
  "SECRETS": "/mystuff/secrets",
  "TMPPATH": "/tmp",
  "STATE": {
    "prod": "prod-state",
    "stage": "stage-state",
    "qa": "qa-state"
  }
}

State refers to the S3 bucket names