import glob, os, sys, shutil, time, json, csv, re, io
import urllib.request
import stat
import zipfile
import subprocess
import requests
import platform
import boto3
import pandas as pd

from mccloud.constants import *

class Cloudy:
    """
    Cloudy

    This allows us to pass all our environment variables and
    make them available to all of the methods

    verbose is set by clicks multichain

    """

    def __init__(self, config):
        self.config = config

    def aws_profile(self):
        if self.env != 'base':
            os.environ['AWS_PROFILE'] = self.env
            os.environ['AWS_SDK_LOAD_CONFIG'] = 'true'

    def initialize_env(self, profile = None, region = None):
        """Return True if env path exists."""
        if self.verify_env():
            self.vprint('\tEnvironment path:' + self.livepath + '\n')
            self.region = self.parse_terraform_config('region')
            self.statebucket = self.config['STATE'][self.env]
            self.statefile = 'terraform.tfstate'
            self.publickey = self.config['PUBLICKEY']
            self.privatekey = self.config['PRIVATEKEY']
            self.vaultpassword = self.config['VAULTPASSWORD']
            self.directorypassword = self.config['DIRECTORYPASSWORD']
            self.aws_profile()
            self.s3 = boto3.resource('s3')
            self.ec2 = boto3.resource('ec2', region_name = self.region)
            self.ds = boto3.client('ds', region_name = self.region)  # No resource available for ds
        else:
            print('Invalid environment path!')
            exit()

    def delete_files_regex(self, dir, pattern):
        """Delete files based on Regular Expression"""
        for f in os.listdir(dir):
            if re.search(pattern, f):
                os.remove(os.path.join(dir, f))

    def verify_env(self):
        """Return True if env path exists."""
        self.livepath = self.config['IACPATH'] + '/terraform/live/' + self.env
        self.tmppath = self.config['TMPPATH'] + '/' + self.env
        if self.exists(self.livepath) and self.env in self.config['STATE']:
            return True
        return False

    def write_variable_to_file(self, var, filename, perms):
        f = open(filename, 'w' )
        f.write(var + '\n')
        f.close()
        os.system('chmod ' + perms + ' ' + filename)

    def parse_terraform_config(self, element):
        """Parses variables stored in the Terraform config file

        We're using this file as the central store of variables for an AWS region
        Returns a string or array depending upon the variable type
        """
        file = self.livepath + '/terraform.tfvars'
        with open(file, "r") as f:
            for line in f:
                if element == 'includeResources' and element in line:
                    dirs = line.split("=")[1].strip()
                    dircsv = re.sub('["]', '', dirs)
                    return dircsv.split(',')
                if element == 'packerSubnet' or 'packerSecuritygroup':
                    if element in line:
                        match = line.split("=")[1].strip()
                        return re.sub('["]', '', match)
                if element == 'region' and element in line:
                    region = line.split("=")[1].strip()
                    region = region.replace('"', '')
                    return region
        return False

    def vprint(self, mystring):
        """ Verbose printing """
        if hasattr(self, 'verbose'):
            print(mystring)

    def subp(self, command):
        """ Shortcut for subprocess """
        self.vprint('\tLaunching: ' + command)
        if hasattr(self, 'verbose'):
            exitvalue = os.system(command)
            if exitvalue != 0:
                print("Something went wrong")
                exit()
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

    def ec2_security_group_id_from_name_tag(self, name):
        """Get an EC2 Security Group ID from Name Tag"""
        filters = [{"Name":"group-name", "Values": [name]}]
        security_groups = list(self.ec2.security_groups.filter(Filters=filters))
        if not security_groups:
            print("No Security Group: " + name + " found. Please make sure it's created")
            exit(1)
        else:
            for item in security_groups: return item.id    # Return first resource

    def ec2_subnet_id_from_name_tag(self, name):
        """Get an EC2 Subnet ID from Name Tag"""
        filters = [{'Name':'tag:Name', 'Values':[name]}]
        subnets = list(self.ec2.subnets.filter(Filters=filters))
        if not subnets:
            print("No Subnet: " + name + " found. Please make sure it's created")
            exit(1)
        else:
            for item in subnets: return item.id    # Return first resource

    def ec2_instance_from_tag(self, vpc, tag):
        vpc = self.ec2.Vpc(vpc)
        filters = [{'Name':'tag:group', 'Values':[tag]}]
        instances = vpc.instances.filter(Filters=filters)
        for instance in instances:
            return instance

    def ec2_public_ip_from_instance(self, instance):
        return instance.public_ip_address

    def get_vpc_id(self):
        filters = [{'Name':'tag:Name', 'Values':['terraform*']}]
        vpcs = self.ec2.vpcs.filter(Filters=filters)
        for vpc in vpcs:
            return vpc.id

    def ec2_instance_name_tag(self, instance):
        for tags in instance.tags:
            if tags["Key"] == 'Name':
                return tags["Value"]
        return "None"

    def list_ec2_instances(self):
        """List EC2 instances"""
        self.initialize_env()
        instances = self.ec2.instances.filter(
            Filters=[{'Name': 'instance-state-name', 'Values': ['running']}])
        instance_count = sum(1 for _ in instances.all())
        RunningInstances = []
        for instance in instances:
            id = instance.id
            name = self.ec2_instance_name_tag(instance)
            type = instance.instance_type
            ip = instance.public_ip_address
            mylist = {"name":name,"id":id,"type":type,"ip":ip}
            #mylist = {"name":name,"ip":ip}
            RunningInstances.append(mylist.copy())
        table = pd.DataFrame.from_dict(RunningInstances)
        check = table.style.render()
        self.write_variable_to_file(check, '/tmp/instances.html', '777')
        print('/tmp/instances.html')

    def set_perms_on_ami(self, ami_id, account):
        account=1234567
        print(perms)
        #aws ec2 modify-image-attribute --image-id ami-e548fe9a --launch-permission "{\"Add\": [{\"UserId\":account"}]}"

    def launch_instance_from_ami(self, ami_id):
        self.initialize_env()
        self.ec2.create_instances(ImageId=ami_id, MinCount=1, MaxCount=1)

    def build_ami_from_running_instance(self, instance_id):
        """
        Step 1: Get the size of the root volume
        Step 2: Get the Instance Name Tag
                'SnapshotId': 'string',
        Step 2: Create AMI
        """
        #from pprint import pprint
        self.initialize_env()
        instance = self.ec2.Instance(instance_id)
        instance_name = self.ec2_instance_name_tag(instance)
        volumes = instance.volumes.all()
        for v in volumes:
           vsize = v.size
        image = instance.create_image(
            BlockDeviceMappings=[
                {
                    'DeviceName': '/dev/sda1',
                    'Ebs': {
                        'Encrypted': False,
                        'DeleteOnTermination': True,
                        'VolumeSize': vsize,
                        'VolumeType': 'gp2'
                    },
                },
            ],
            Description='Image of ' + instance_name,
            Name=instance_name
        )

    def list_envs(self):
        """List Environments"""
        print('\nAvailable Environments:')
        for f_name in glob.glob(self.config['IACPATH'] + '/terraform/live/*'):
            base = os.path.basename(f_name)
            resource = os.path.splitext(base)[0]
            print('\t' + resource)

    def connect(self):
        self.initialize_env()
        vpc = self.get_vpc_id()
        if vpc:
            instance = self.ec2_instance_from_tag(vpc, self.host)
            public_ip = self.ec2_public_ip_from_instance(instance)
            print('Connect to ' + self.host + ' at ' + public_ip)
            os.system('ssh -o StrictHostKeyChecking=no -i' + self.tmppath + '/id_rsa centos@' + public_ip)
        else:
            print("No VPC's found")
            exit()

    def add_private_key_to_ssh_agent(self):
        """Adds a private key to the local SSH Agent. Assumes you're sitting next to it"""
        os.system('ssh-add id_rsa')

    def create_s3_bucket(self, bucket):
        """ Create an S3 bucket - in case it doesn't exist"""
        try:
            self.s3.create_bucket(Bucket=bucket)
        except botocore.exceptions.ClientError as e:
            if e.response['Error']['Code'] == '404':
                self.vprint('\t\tNo state file found.')
            elif e.response['Error']['Code'] == '403':
                self.vprint('\t\tS3 Bucket Permissions error.')
                exit()
            else:
                raise

    def copy_file_to_s3_bucket(self, bucket, src, dest):
        try:
            self.s3.Bucket(bucket).upload_file(src, dest)
        except botocore.exceptions.ClientError as e:
            if e.response['Error']['Code'] == '404':
                if hasattr(self, 'verbose'):
                    print('\t\tNo state file found.')
            else:
                raise

    def packer_list(self):
        """This option lists the available AMI resources to build"""
        self.initialize_env()
        print("Available AMI's to build:")
        for f_name in glob.glob(self.config['IACPATH'] + '/packer/*.json'):
            base = os.path.basename(f_name)
            resource = os.path.splitext(base)[0]
            print('\t' + resource)

    def packer_deploy(self):
        """

        This option provisions AMI images with Packer and Ansible

        Security Group set to 'packer'

        """
        self.initialize_env()
        print('Deploying Packer on the ' + self.env + ' environment!')
        os.chdir(self.config['IACPATH'] + '/packer')
        region = self.parse_terraform_config('aws_region')
        if hasattr(self, 'firstrun'):
           variables = " -var region=" + region
           self.ami = 'base'
        else:
            subnetname = self.parse_terraform_config('packerSubnet')
            securitygroup = self.ec2_security_group_id_from_name_tag('packer')
            subnet = self.ec2_subnet_id_from_name_tag(subnetname)
            variables = " -var region=" + region + " -var securitygroup=" + securitygroup + " -var subnet=" + subnet
        if not hasattr(self,'ami'):
            self.packer_list()
            ami = input("Which AMI do you want to deploy? ")
            self.ami = ami
        #self.subp('packer build -var ansiblepath=' + self.config['ANSIBLEPATH'] + variables + ' ' + self.ami + '.json')
        os.system('packer build -var ansiblepath=' + self.config['ANSIBLEPATH'] + variables + ' ' + self.ami + '.json')


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

    def get_connect_ip(self):
        """
        Returns the public IP address of the curent address
        """
        self.vprint('\tGetting Connect IP address')
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
        for file in glob.glob(src):
            self.vprint('\t\tCopying this file: ' + file)
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
                self.create_s3_bucket(Bucket=self.statebucket)
            else:
                raise

    def terraform_push_state(self):
        """ Push the current state file to S3 """
        self.vprint('\tPush current state to S3')
        self.copy_file_to_s3_bucket(self.statebucket, self.tmppath + '/' + self.statefile, self.statefile)

    def terraform_copy_resources(self, include_dirs):
        """ Copy incuded resources to temp path """
        self.vprint('\tCopying resources')
        for d in include_dirs:
            if '/' in d:
                directory = d.split('/')[0]
                file = d.split('/')[1] + '.tf'
                self.terraform_copy_folder_files(self.config['IACPATH'] + '/terraform/resources/' + directory + '/' + file, self.tmppath)
            else:
                self.terraform_copy_folder_files(self.config['IACPATH'] + '/terraform/resources/' + d + '/*', self.tmppath)

    def terraform_prep(self):
        self.initialize_env()
        self.vprint('\tRemote state: ' + self.statebucket)
        #self.vprint('\tPrivate Key: ' + self.privatekey)
        include_dirs = self.parse_terraform_config('includeResources')
        connect_ip = self.get_connect_ip()
        self.terraform_merge_env_and_secrets()
        self.terraform_pull_state()
        self.terraform_copy_resources(include_dirs)
        os.chdir(self.tmppath)
        return connect_ip

    def terraform_deploy(self):
        """
        Deploy using Terraform

        Combine resources with environment definitions to build out environments

        Remote state is pulled from S3
        """
        connect_ip = self.terraform_prep()
        deploy = " --var 'directory_password=" + self.directorypassword + "' -var 'connect_ip=" + connect_ip + "'"
        self.subp("terraform init " + deploy)
        self.subp("terraform plan " + deploy)
        #self.subp("terraform apply --auto-approve " + deploy)
        #self.terraform_push_state()
        print('------- Deploy Complete -------\n')
        print('------- Adding the Private Key to the Local SSH Agent -------\n')
        self.add_private_key_to_ssh_agent()


    # Terraform destroys combine resources with environment definitions to build out environments
    def terraform_destroy(self):
        """
        Destroy using Terraform

        Combine resources with environment definitions to build out environments

        Remote state is pulled from S3
        """
        connect_ip = self.terraform_prep()
        deploy = " --var 'directory_password=" + self.directorypassword + "' -var 'connect_ip=" + connect_ip + "'"
        self.subp("terraform init " + deploy)
        self.subp("terraform destroy -auto-approve " + deploy)
        self.terraform_push_state()
        print('------- Destroy Complete -------')


    def terraform_dns(self):
        connect_ip = self.terraform_prep()
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

    def print_key(self, file, type):
        with open(file,"rb") as f:
           contents = f.read().replace(b"\n",b"\\n")
        keystr = contents.decode("utf-8").replace("b'","'")
        if type == 'private':
            print('"PRIVATEKEY": "' + keystr + '",')
        else:
            print('"PUBLICKEY": "' + keystr + '"')

    def list_rds_instances(self):
        os.system("aws rds describe-db-instances --query 'DBInstances[*].[DBInstanceIdentifier]' --region us-east-1 --output text")

    def generate_ssh_keys(self):
        """Generate a Key Pair and print them here to add them to config.json"""
        # replace = "awk '{printf \"%s\\\\n\", $0}' /tmp/terraform"
        # os.system(replace)
        self.delete_files_regex('/tmp', '^terraform.*')    # Remove any old keys
        os.system("ssh-keygen -f /tmp/terraform -t rsa -N '' > /dev/null 2>&1")
        self.print_key('/tmp/terraform', 'private') # Print Private key as string with newlines
        self.print_key('/tmp/terraform.pub', 'public')
        print('Copy private key to S3 Bucket')
        self.s3 = boto3.resource('s3')
        self.create_s3_bucket(self.config['STATE']['base'])
        self.copy_file_to_s3_bucket(self.config['STATE']['base'], '/tmp/terraform', 'terraform.pem')

    def generate_ssh_keys_native(self):
        from OpenSSL import crypto
        k = crypto.PKey()
        k.generate_key(crypto.TYPE_RSA, 4096)
        print(crypto.dump_privatekey(crypto.FILETYPE_PEM, k))
        print(crypto.dump_publickey(crypto.FILETYPE_PEM, k))

    def searchs3bucket(self, bucket, string):
        """Get a list of keys in an S3 bucket."""
        keys = []
        self.initialize_env()
        client = boto3.client('s3', region_name=self.region)
        resp = client.list_objects_v2(Bucket=bucket)
        for obj in resp['Contents']:
            if string in obj['Key']:
                print(obj['Key'])
            #keys.append(obj['Key'])
        #return keys
