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

    env, verbose are set by clicks multichain

    """

    def __init__(self, config):
        self.config = config
        self.iacpath = config['IACPATH']
        self.binpath = config['BINPATH']
        self.ansiblepath = config['ANSIBLEPATH']
        self.privatekey = config['PRIVATEKEY']
        self.publickey = config['PUBLICKEY']
        self.vaultpassword = config['VAULTPASSWORD']
        self.directorypassword = config['DIRECTORYPASSWORD']
        if 'CUSTOMCREDSFILE' in config:
            self.customcreds = config['CUSTOMCREDSFILE']
        else:
            self.customcreds = ''
        self.livepath = ''
        self.tmppath = ''
        self.verbose = ''
        self.ami = ''
        self.host = ''

    def initialize_env(self, region = None):
        """Return True if env path exists."""
        if self.customcreds != '':
            os.environ["AWS_SHARED_CREDENTIALS_FILE"] = self.customcreds
            self.vprint(os.environ["AWS_SHARED_CREDENTIALS_FILE"])
            self.ec2 = boto3.resource('ec2', region_name = region)
            return False
        self.livepath = self.iacpath + '/terraform/live/' + self.env
        self.tmppath = self.config['TMPPATH'] + '/' + self.env
        if self.env != 'none':
            self.vprint('\tEnvironment path:' + self.livepath + '\n')
            self.region = self.parse_region()
            self.statebucket = self.config['STATE'][self.env]
            self.statefile = 'terraform.tfstate'
            self.s3 = boto3.resource('s3')
            self.ec2 = boto3.resource('ec2', region_name = self.region)
            self.ds = boto3.resource('ds', region_name = self.region)
        if self.env == 'none' or self.exists(self.livepath):
            return True
        return False

    def write_variable_to_file(self, var, filename, perms):
        f = open(filename, 'w' )
        f.write(var + '\n')
        f.close()
        os.system('chmod ' + perms + ' ' + filename)

    def parse_directories(self):
        """ Returns an array of directories to include in Terraform deploy """
        file = self.livepath + '/terraform.tfvars'
        with open(file, "r") as f:
            for line in f:
                if 'include' in line:
                    dirs = line.split("=")[1].strip()
                    dircsv = re.sub('["]', '', dirs)
        return dircsv.split(',')

    def parse_region(self):
        """ Returns the region for the current environment """
        file = self.livepath + '/terraform.tfvars'
        with open(file, "r") as f:
            for line in f:
                if 'aws_region' in line:
                    region = line.split("=")[1].strip()
                    region = region.replace('"', '')
        return region

    def vprint(self, mystring):
        """ Verbose printing """
        if self.verbose:
            print(mystring)

    def subp(self, command):
        """ Shortcut for subprocess """
        self.vprint('\tLaunching: ' + command)
        if self.verbose:
            os.system(command)
        else:
            output = subprocess.check_output(command, stderr=subprocess.STDOUT, shell=True)
        #output = proc.stderr.read()
        #self.vprint(output)

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

    def get_instance_from_tag(self, vpc, tag):
        vpc = self.ec2.Vpc(vpc)
        filters = [{'Name':'tag:group', 'Values':[tag]}]
        instances = vpc.instances.filter(Filters=filters)
        for instance in instances:
            return instance

    def get_public_ip_from_instance(self, instance):
        return instance.public_ip_address

    def get_vpc_id(self):
        filters = [{'Name':'tag:Name', 'Values':['terraform*']}]
        vpcs = self.ec2.vpcs.filter(Filters=filters)
        for vpc in vpcs:
            return vpc.id
        
    def connect(self):
        self.initialize_env()
        vpc = self.get_vpc_id()
        if vpc:
            instance = self.get_instance_from_tag(vpc, self.host)
            public_ip = self.get_public_ip_from_instance(instance)
            print('Connect to ' + self.host + ' at ' + public_ip)
            os.system('ssh -o StrictHostKeyChecking=no -i' + self.tmppath + '/id_rsa centos@' + public_ip)
        else:
            print("No VPC's found")
            exit()

    def packer_list(self):
        """This option lists the available AMI resources to build"""
        print("Available AMI's to build:")
        self.initialize_env()
        for f_name in glob.glob(self.iacpath + '/packer/*.json'):
            base = os.path.basename(f_name)
            resource = os.path.splitext(base)[0]
            print('\t' + resource)

    def packer_deploy(self):
        """This option provisions AMI images with Packer and Ansible"""
        self.initialize_env()
        print('Deploying Packer on the ' + self.env + ' environment!')
        os.chdir(self.iacpath + '/packer')
        region = self.parse_region()
        self.subp('packer build -var ansiblepath=' + self.ansiblepath + ' -var region=' + region + ' ' + self.ami + '.json')

    def ansible_deploy(self, playbook):
        ssh_user = 'centos'

        os.environ['TF_STATE'] = CURPATH + '/terraform/' + self.env + '/terraform.tfstate'

        response = exists('terraform/' + self.env + '/terraform.tfstate')

        if response == True:
            self.subp('cd ansible && ansible-playbook playbooks/' + playbook + '.yml -i inventory/terraform -e "ansible_ssh_user=' + ssh_user + '" --private-key ../terraform/' + self.env + '/id_rsa')
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
            self.subp('cd ansible && ansible ' + host + ' -a "' + cmd + '" -u ' + ssh_user + ' -i inventory/terraform  --private-key ../terraform/' + env + '/id_rsa')            
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
        shutil.copyfile(self.livepath + '/terraform.tfvars', self.tmppath + '/terraform.tfvars')
        self.write_variable_to_file(self.publickey, self.tmppath + '/id_rsa.pub', '600')
        #shutil.copyfile(self.secrets + '/id_rsa.pub', self.tmppath + '/id_rsa.pub')
        self.write_variable_to_file(self.vaultpassword, self.tmppath + '/vault_password_file', '600')
        #shutil.copyfile(self.secrets + '/vault_password_file', self.tmppath + '/vault_password_file')
        self.write_variable_to_file(self.privatekey, self.tmppath + '/id_rsa', '600')

    def terraform_create_bucket(self):
        """ Create an S3 bucket - in case it doesn't exist"""
        try:
            self.s3.create_bucket(Bucket=self.statebucket)
        except botocore.exceptions.ClientError as e:
            if e.response['Error']['Code'] == '404':
                self.vprint('\t\tNo state file found.')
            elif e.response['Error']['Code'] == '403':
                self.vprint('\t\tS3 Bucket Permissions error.')
                exit()
            else:
                raise

    def terraform_pull_state(self):
        """ Pull a state file from S3 """
        self.vprint('\tPull remote state')

        try:
            self.s3.Bucket(self.statebucket).download_file(self.statefile, self.tmppath + '/' + self.statefile)
        except botocore.exceptions.ClientError as e:
            if e.response['Error']['Code'] == '404':
                self.vprint('\t\tNo state file found.')
            elif e.response['Error']['Code'] == '403':
                self.vprint('\t\tNo bucket found. Creating it.')
                self.terraform_create_bucket
            else:
                raise

    def terraform_push_state(self):
        """ Push the current state file to S3 """
        self.vprint('\tPush current state to S3')

        try:
            self.s3.Bucket(self.statebucket).upload_file(self.tmppath + '/' + self.statefile, self.statefile)
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

    def terraform_prep(self):
        self.initialize_env()
        self.vprint('\tRemote state: ' + self.statebucket)
        self.vprint('\tPublic Key: ' + self.publickey)
        include_dirs = self.parse_directories()
        home_ip = self.get_home_ip()
        self.terraform_merge_env_and_secrets()
        self.terraform_pull_state()
        self.terraform_copy_resources(include_dirs)
        os.chdir(self.tmppath)
        return home_ip

    def terraform_deploy(self):
        """
        Deploy using Terraform 
        
        Combine resources with environment definitions to build out environments

        Remote state is pulled from S3
        """
        home_ip = self.terraform_prep()
        deploy = " --var 'directory_password=" + self.directorypassword + "' -var 'home_ip=" + home_ip + "'"
        self.subp("terraform init " + deploy)
        self.subp("terraform plan " + deploy)
        self.subp("terraform apply --auto-approve " + deploy)
        self.terraform_push_state()
        print('------- Deploy Complete -------')

    # Terraform destroys combine resources with environment definitions to build out environments
    def terraform_destroy(self):
        """
        Destroy using Terraform 
        
        Combine resources with environment definitions to build out environments

        Remote state is pulled from S3
        """
        home_ip = self.terraform_prep()
        deploy = " --var 'directory_password=" + self.directorypassword + "' -var 'home_ip=" + home_ip + "'"
        self.subp("terraform init " + deploy)
        self.subp("terraform destroy -auto-approve " + deploy)
        self.terraform_push_state()
        print('------- Destroy Complete -------')


    def terraform_dns(self):
        home_ip = self.terraform_prep()
        for directory in self.ds.describe_directories()['DirectoryDescriptions']:
            return(directory['Name'])

    def find_centos7_image(self):
        response = self.ec2.describe_images(
            Owners=['679593333241'], # CentOS
            Filters=[
                {'Name': 'name', 'Values': ['CentOS Linux 7 x86_64 HVM EBS *']},
                {'Name': 'architecture', 'Values': ['x86_64']},
                {'Name': 'root-device-type', 'Values': ['ebs']},
            ],
        )

        amis = sorted(response['Images'],
              key=lambda x: x['CreationDate'],
              reverse=True)
        return amis[0]['ImageId']

    def create_keypair(self, keyname):
        return self.ec2.create_key_pair(
            KeyName=keyname
        )

    def wait_ec2_complate(self, client, instance_id):
        """
        this method is to make client keep sending request until ec2 instance building complate or fail
        :param client:
        :param instance_name:
        :return:
        """
        while True:
            time.sleep(10)
            rsp = client.describe_instance_status(
                InstanceIds=[str(instance_id)],
                IncludeAllInstances=True
            )
            # double check 2/2 status
            instance_status = rsp['InstanceStatuses'][0]['InstanceStatus']['Status']
            system_status = rsp['InstanceStatuses'][0]['SystemStatus']['Status']

            if str(instance_status) == 'ok' and str(system_status) == 'ok':
                status = True
                break
            if str(instance_status) == 'impaired' or str(instance_status) == 'insufficient-data' or \
                            str(instance_status) == 'not-applicable' or str(system_status) == 'failed' or \
                            str(system_status) == 'insufficient-data':
                status = False
                #print('Instance status is ' + str(instance_status))
                #print('System status is ' + str(system_status))
                break
            if time >= POLL_TIMES:
                break
        return status

    def send_command_to_instance(self, instance_id, keypath, command):
        filters = [{'Name':'instance-id', 'Values':[instance_id]}]
        myinstance = list(self.ec2.instances.filter(Filters=filters))[0]
        public_ip = self.get_public_ip_from_instance(myinstance)
        print('ssh -o StrictHostKeyChecking=no -i ' + keypath + ' centos@' + public_ip + ' "' + command + '"')
        os.system('ssh -o StrictHostKeyChecking=no -i ' + keypath + ' centos@' + public_ip + ' "' + command + '"')

    def create_base_image(self, region='us-east-1'):
        """Create a base image from the Centos 7 AMI"""
        self.initialize_env(region)
        # Get the latest Centos 7 AMI - cache it for now
        #  centos7image = self.find_centos7_image()
        centos7image = "ami-b81dbfc5"
        # Create a keypair for the instance and save privatekey for connecting
        privatekey = self.create_keypair('converter').key_material
        keypath = '/tmp/id_rsa'
        self.write_variable_to_file(privatekey, keypath, '600')
        #print(privatekey)
        availability_zone = region + 'd'
        # Launch an EC2 instance with Centos 7 image
        instance = self.ec2.create_instances(
           ImageId=centos7image, 
           MinCount=1, 
           MaxCount=1,
           KeyName="converter",
           InstanceType="t2.micro",
           Placement={
             'AvailabilityZone': availability_zone
           }
        )
        instance_id = instance[0].id
        #client = self.ec2
        #self.wait_ec2_complate(client, instance_id)
        print('Waiting for instace to start: ' + instance_id)
        time.sleep(30)
        # Create an 8gb volume
        volume = self.ec2.create_volume(
            AvailabilityZone=availability_zone,
            Size=8
        )
        print('Waiting for volume to be available: ' + volume.id)
        time.sleep(20)
        # Atach the volume to the instance
        self.ec2.Instance(instance_id).attach_volume(VolumeId=volume.id, Device='/dev/sdf')
        self.send_command_to_instance(instance_id, keypath, 'mkfs -t ext4 /dev/xvdf')
        self.send_command_to_instance(instance_id, keypath, 'dd bs=1M if=/dev/xvda of=/dev/xvdf')
        self.ec2.Instance(instance_id).stop_instance()
        # detach root volume - delete it
        # detach second volume and attach as root volume
        # create image from instance
        #  self.ec2.create_image

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
