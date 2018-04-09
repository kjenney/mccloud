import glob, os, sys, shutil, time, json, csv, re, io
import urllib.request
import stat
import zipfile
import subprocess
import requests
import platform
import boto3
import botocore

from mccloud.constants import *

def read_config():
    file = CURPATH + '/config.json'
    try:
        st = os.stat(file)
    except os.error:
        return False
    return json.load(open(file))

class Cloudy:
    """
    Cloudy

    This allows us to pass all our environment variables and
    make them available to all of the methods

    """

    def __init__(self, config, env, verbose):
        self.config = config
        self.env = env
        self.verbose = verbose
        self.iacpath = config['IACPATH']
        self.binpath = config['BINPATH']
        self.secrets = config['SECRETS']
        self.tmppath = config['TMPPATH'] + '/' + env
        if self.env != 'none':
            self.remotestate = config['STATE'][env]
        self.tpath = self.iacpath + '/terraform/live/' + self.env

    def verify_env(self):
        """Return True if env path exists."""
        if self.env != 'none':
            self.vprint('\tEnvironment path: ' + self.tpath + '\n')
        if self.env == 'none' or self.exists(self.tpath):
            return True
        return False

    def parse_vars(self):
        """ Returns an array of directories to include in Terraform deploy """
        file = self.tpath + '/terraform.tfvars'
        with open(file, "r") as f:
            for line in f:
                if 'include' in line:
                    dirs = line.split("=")[1].strip()
                    dircsv = re.sub('["]', '', dirs)
        return dircsv.split(',')

    def vprint(self, mystring):
        """ Verbose printing """
        if self.verbose:
            print(mystring)

    def subp(self, command):
        """ Shortcut for subprocess """
        self.vprint('\tLaunching: ' + command)
        ret = subprocess.call(command, shell=True)

    def download_file(self, url, file_name):
        """ Download a file from the web """
        urllib.request.urlretrieve(url, file_name)

    def make_exeutable(self, path):
        """ Make a file executable """
        os.chmod(path, stat.S_IXUSR | stat.S_IRUSR | stat.S_IRGRP | stat.S_IXGRP | stat.S_IROTH | stat.S_IXOTH)

    def remove_file(self, path):
        """ Remove directory or file """
        try:
            os.remove(path)
        except OSError:
            pass

    def unzip_file(self, filename):
        #print("Opening file", filename)
        with open(filename, 'rb') as f:
            #print("  Unzipping file", filename)
            z = zipfile.ZipFile(f)
            for name in z.namelist():
                #print('    Extracting file', name)
                z.extract(name,"/tmp/")

    def exists(self, path):
        """Test whether a path exists.  Returns False for broken symbolic links"""
        try:
            st = os.stat(path)
        except os.error:
            return False
        return True

    def packer_deploy(self):
        print('Works on the ' + self.env + ' environment!')

    def ansible_deploy(self, playbook):
        ssh_user = 'centos'

        os.environ['TF_STATE'] = CURPATH + '/terraform/' + self.env + '/terraform.tfstate'

        response = exists('terraform/' + self.env + '/terraform.tfstate')

        if response == True:
            ret = subprocess.call('cd ansible && ansible-playbook playbooks/' + playbook + '.yml -i inventory/terraform -e "ansible_ssh_user=' + ssh_user + '" --private-key ../terraform/' + self.env + '/id_rsa', shell=True)
        else:
            print("Path not found:" + 'terraform/' + self.env + '/terraform.tfstate')

    def ansible_command(self, host, cmd):
        ssh_user = 'centos'

        if not host:
            print('Host or Hostgroup is required.')
            exit()

        if not cmd:
            print('Command is required.')
            exit()

        os.environ['TF_STATE'] = CURPATH + '/terraform/' + self.env + '/terraform.tfstate'
        os.environ['TF_ANSIBLE_GROUPS_TEMPLATE'] = '{{ ["jump", "tf_tags[group]"] | join("\n") }}'

        response = exists('terraform/' + self.env + '/terraform.tfstate')

        if response == True:
            ret = subprocess.call('cd ansible && ansible ' + host + ' -a "' + cmd + '" -u ' + ssh_user + ' -i inventory/terraform  --private-key ../terraform/' + env + '/id_rsa', shell=True)
            
        else:
            print("Path not found: " + 'terraform/' + self.env + '/terraform.tfstate')

    def get_home_ip(self):
        """ 
        Returns the public IP address of the curent address
        """
        self.vprint('\tGetting Home IP address')
        my_ip = requests.get("http://ipecho.net/plain?").text
        self.vprint('\t\t' + my_ip + '/32')
        return my_ip + '/32'

    def recreate_dir(self, path):
        if self.exists(path):
            shutil.rmtree(path)
            os.makedirs(path)
        else:
            os.makedirs(path)

    def copy_recursive(self, src, dest):
        for file in glob.glob(src + '/*/*'):
            shutil.copy(file, dest)

    def terraform_copy_folder_files(self, src, dest):
        for file in glob.glob(src + '/*'):
            shutil.copy(file, dest)

    def terraform_merge_env_and_secrets(self):
        self.vprint('\tMerge environment and secrets')
        self.recreate_dir(self.tmppath)
        shutil.copyfile(self.tpath + '/terraform.tfvars', self.tmppath + '/terraform.tfvars')
        shutil.copyfile(self.secrets + '/id_rsa.pub', self.tmppath + '/id_rsa.pub')
        shutil.copyfile(self.secrets + '/vault_password_file', self.tmppath + '/vault_password_file')

    def terraform_pull_state(self):
        """ Pull a state file from S3 """
        self.vprint('\tPull remote state')

        bucket = self.remotestate
        file = 'terraform.tfstate'

        s3 = boto3.resource('s3')

        try:
            s3.Bucket(bucket).download_file(file, self.tmppath + '/' + file)
        except botocore.exceptions.ClientError as e:
            if e.response['Error']['Code'] == '404':
                if self.verbose:
                    print('\t\tNo state file found.')
            else:
                raise

    def terraform_push_state(self):
        """ Push the current state file to S3 """
        self.vprint('\tPush current state to S3')

        bucket = self.remotestate
        file = 'terraform.tfstate'

        s3 = boto3.resource('s3')

        try:
            s3.Bucket(bucket).upload_file(self.tmppath + '/' + file, file)
        except botocore.exceptions.ClientError as e:
            if e.response['Error']['Code'] == '404':
                if self.verbose:
                    print('\t\tNo state file found.')
            else:
                raise

    def terraform_copy_resources(self, include_dirs):
        """ Copy incuded resources to temp path """
        self.vprint('\tCopying resources')
        for d in include_dirs:
            self.terraform_copy_folder_files(self.iacpath + '/terraform/resources/' + d, self.tmppath)

    def terraform_deploy(self):
        """
        Deploy using Terraform 
        
        Combine resources with environment definitions to build out environments

        Remote state is pulled from S3
        """
        self.vprint('\tRemote state: ' + self.remotestate)
        include_dirs = self.parse_vars()
        home_ip = self.get_home_ip()
        self.terraform_merge_env_and_secrets()
        self.terraform_pull_state()
        self.terraform_copy_resources(include_dirs)
        os.chdir(self.tmppath)
        self.subp("terraform init -var 'home_ip=" + home_ip + "'")
        self.subp("terraform plan -var 'home_ip=" + home_ip + "'")
        self.subp("terraform apply --auto-approve -var 'home_ip=" + home_ip + "'")
        self.terraform_push_state()

    # Terraform destroys combine resources with environment definitions to build out environments
    def terraform_destroy(self):
        """
        Destroy using Terraform 
        
        Combine resources with environment definitions to build out environments

        Remote state is pulled from S3
        """
        self.vprint('\tRemote state: ' + self.remotestate)
        include_dirs = self.parse_vars()
        home_ip = self.get_home_ip()
        self.terraform_merge_env_and_secrets()
        self.terraform_pull_state()
        self.terraform_copy_resources(include_dirs)
        os.chdir(self.tmppath)
        self.subp("terraform init -var 'home_ip=" + home_ip + "'")
        self.subp("terraform destroy -auto-approve -var 'home_ip=" + home_ip + "'")
        self.terraform_push_state()

    def build_scaffold(self, dir):
        print('Building Scaffold in: %s' % dir)

    def extract_tool_from_web_to_env(self, url, tool, dest):
        file_name = url[url.rfind("/")+1:]
        self.download_file(url, '/tmp/' + file_name)
        self.unzip_file('/tmp/' + file_name)
        self.remove_file(dest + tool)
        shutil.copyfile('/tmp/' + tool, dest + tool)
        self.make_exeutable(dest + tool)
        self.vprint('\tInstalled ' + tool)

    # Assumes 64-bit OS
    def install_tools(self):
        print('Installing Tools')
        dest = self.config['BINPATH'] + '/'
        dist = (platform.system()).lower()
        baseurl = 'https://releases.hashicorp.com/'
        self.extract_tool_from_web_to_env(baseurl + 'terraform/0.11.6/terraform_0.11.6_' + dist + '_amd64.zip','terraform', dest)
        self.extract_tool_from_web_to_env(baseurl + 'packer/1.2.2/packer_1.2.2_' + dist + '_amd64.zip', 'packer', dest)
        self.extract_tool_from_web_to_env(baseurl + 'nomad/0.7.1/nomad_0.7.1_' + dist + '_amd64.zip', 'nomad', dest)
        self.remove_file(dest + 'terragrunt')
        self.download_file('https://github.com/gruntwork-io/terragrunt/releases/download/v0.14.7/terragrunt_' + dist + '_amd64', dest + 'terragrunt')
        self.make_exeutable(dest + 'terragrunt')
        self.vprint('\tInstalled terragrunt')
        print('\tInstalled all tools')
