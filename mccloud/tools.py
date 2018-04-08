import glob, os, sys, shutil, time, json, csv, re
import urllib.request
import stat
import zipfile
import subprocess
import requests
import io
import platform

import mccloud.constants


# Returns an array of directories to include in Terraform deploy
def parse_vars(env):
    file = 'terraform/live/' + env + '/terraform.tfvars'
    with open(file, "r") as f:
        for line in f:
            if 'include' in line:
                dirs = line.split("=")[1].strip()
                dircsv = re.sub('["]', '', dirs)
    return dircsv.split(',')

def packer_deploy(env):
    print('Works on the ' + env + ' environment!')

def ansible_deploy(env, playbook):
    ssh_user = 'centos'

    os.environ['TF_STATE'] = constants.CURPATH + '/terraform/' + env + '/terraform.tfstate'

    response = exists('terraform/' + env + '/terraform.tfstate')

    if response == True:
        ret = subprocess.call('cd ansible && ansible-playbook playbooks/' + playbook + '.yml -i inventory/terraform -e "ansible_ssh_user=' + ssh_user + '" --private-key ../terraform/' + env + '/id_rsa', shell=True)
    else:
        print("Path not found:" + 'terraform/' + env + '/terraform.tfstate')

def ansible_command(env, host, cmd):
    ssh_user = 'centos'

    if not host:
        print('Host or Hostgroup is required.')
        exit()

    if not cmd:
        print('Command is required.')
        exit()

    os.environ['TF_STATE'] = constants.CURPATH + '/terraform/' + env + '/terraform.tfstate'
    os.environ['TF_ANSIBLE_GROUPS_TEMPLATE'] = '{{ ["jump", "tf_tags[group]"] | join("\n") }}'

    response = exists('terraform/' + env + '/terraform.tfstate')

    if response == True:
        ret = subprocess.call('cd ansible && ansible ' + host + ' -a "' + cmd + '" -u ' + ssh_user + ' -i inventory/terraform  --private-key ../terraform/' + env + '/id_rsa', shell=True)
        
    else:
        print("Path not found: " + 'terraform/' + env + '/terraform.tfstate')

def get_home_ip():
    my_ip = requests.get("http://ipecho.net/plain?").text
    return my_ip + '/32'

def recreate_dir(path):
    if exists(path):
        shutil.rmtree(path)
        os.makedirs(path)
    else:
        os.makedirs(path)

def copy_recursive(src, dest):
    for file in glob.glob(src + '/*/*'):
        shutil.copy(file, dest)

def copy_folder_files(src, dest):
    for file in glob.glob(src + '/*'):
        shutil.copy(file, dest)

def merge_terraform_files(env):
    tmp_path = "/tmp/" + env
    recreate_dir(tmp_path)
    shutil.copyfile('terraform/live/' + env + '/terraform.tfvars', tmp_path + '/terraform.tfvars')
    if exists('terraform/live/' + env + '/terraform.tfstate'):
        shutil.copyfile('terraform/live/' + env + '/terraform.tfstate', tmp_path + '/terraform.tfstate')
    shutil.copyfile('secrets/id_rsa.pub', tmp_path + '/id_rsa.pub')
    shutil.copyfile('secrets/vault_password_file', tmp_path + '/vault_password_file')

def copy_back_state(env):
    curpath = mccloud.constants.CURPATH
    tmp_path = "/tmp/" + env
    shutil.copyfile(tmp_path + '/terraform.tfstate', curpath + '/terraform/live/' + env + '/terraform.tfstate')
    if exists(tmp_path + '/terraform.tfstate.backup'):
        shutil.copyfile(tmp_path + '/terraform.tfstate.backup', curpath + '/terraform/live/' + env + '/terraform.tfstate.backup')

# Terraform deploys combine resources with environment definitions to build out environments
def terraform_deploy(env):
    include_dirs = parse_vars(env)
    tmp_path = "/tmp/" + env
    home_ip = get_home_ip()
    merge_terraform_files(env)
    for d in include_dirs:
        copy_folder_files('terraform/resources/' + d,tmp_path)
    os.chdir(tmp_path)
    ret = subprocess.call("terraform init -var 'home_ip=" + home_ip + "'", shell=True)
    ret = subprocess.call("terraform plan -var 'home_ip=" + home_ip + "'", shell=True)
    ret = subprocess.call("terraform apply --auto-approve -var 'home_ip=" + home_ip + "'", shell=True)
    copy_back_state(env)

# Terraform destroys combine resources with environment definitions to build out environments
def terraform_destroy(env):
    include_dirs = parse_vars(env)
    tmp_path = "/tmp/" + env
    home_ip = get_home_ip()
    merge_terraform_files(env)
    for d in include_dirs:
        copy_folder_files('terraform/resources/' + d,tmp_path)
    os.chdir(tmp_path)
    ret = subprocess.call("terraform init -var 'home_ip=" + home_ip + "'", shell=True)
    ret = subprocess.call("terraform destroy -auto-approve -var 'home_ip=" + home_ip + "'", shell=True)

def exists(path):
    """Test whether a path exists.  Returns False for broken symbolic links"""
    try:
        st = os.stat(path)
    except os.error:
        return False
    return True

def build_scaffold(dir):
    print('Building Scaffold in: %s' % dir)

def unzip_file(filename):
    #print("Opening file", filename)
    with open(filename, 'rb') as f:
        #print("  Unzipping file", filename)
        z = zipfile.ZipFile(f)
        for name in z.namelist():
            #print('    Extracting file', name)
            z.extract(name,"/tmp/")

def download_file(url, file_name):
    urllib.request.urlretrieve(url, file_name)

def make_exeutable(path):
    os.chmod(path, stat.S_IXUSR | stat.S_IRUSR | stat.S_IRGRP | stat.S_IXGRP | stat.S_IROTH | stat.S_IXOTH)

def remove_file(path):
    try:
        os.remove(path)
    except OSError:
        pass

def extract_tool_from_web_to_env(url, tool, dest):
    file_name = url[url.rfind("/")+1:]
    download_file(url, '/tmp/' + file_name)
    unzip_file('/tmp/' + file_name)
    remove_file(dest + tool)
    shutil.copyfile('/tmp/' + tool, dest + tool)
    make_exeutable(dest + tool)
    print('Installed ' + tool)

# Assumes 64-bit OS
def install_tools(dest):
    dist = (platform.system()).lower()
    baseurl = 'https://releases.hashicorp.com/'
    extract_tool_from_web_to_env(baseurl + 'terraform/0.11.6/terraform_0.11.6_' + dist + '_amd64.zip','terraform', dest)
    extract_tool_from_web_to_env(baseurl + 'packer/1.2.2/packer_1.2.2_' + dist + '_amd64.zip', 'packer', dest)
    extract_tool_from_web_to_env(baseurl + 'nomad/0.7.1/nomad_0.7.1_' + dist + '_amd64.zip', 'nomad', dest)
    remove_file(dest + 'terragrunt')
    download_file('https://github.com/gruntwork-io/terragrunt/releases/download/v0.14.7/terragrunt_' + dist + '_amd64', dest + 'terragrunt')
    make_exeutable(dest + 'terragrunt')
    print('Installed terragrunt')
