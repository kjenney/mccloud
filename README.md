# mccloud

A tool to administer AWS...

Uses Terraform, Ansible, and a host of other tools to make life easier.

Config is pulled from config.json in the working directory. All secrets are in this file. It should NOT be checked into git.

```{
  "BINPATH": "/mystuff/.env/bin",
  "ANSIBLEPATH": "/mystuff/ansible-repo",
  "IACPATH": "/mystuff/iac_example",
  "TMPPATH": "/tmp",
  "STATE": {
    "prod": "prod-state",
    "stage": "stage-state",
    "qa": "qa-state"
  },
  "VAULTPASSWORD": "myvaultpassword",
  "PRIVATEKEY": "-----BEGIN RSA PRIVATE KEY-----\n...",
  "PUBLICKEY": "-----BEGIN RSA PUBLIC KEY-----\n..."
}
```

State refers to the S3 bucket names.
Private and public keys are used for the AWS key pair.
Vault Password will be used to deccrypt Ansible secrets.
