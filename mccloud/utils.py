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

class Utils(Cloudy):
    """
    Utils

    Useful methods and interactions to go with Cloudy

    """

    def delete_files_regex(self, dir, pattern):
        """Delete files based on Regular Expression"""
        for f in os.listdir(dir):
            if re.search(pattern, f):
                os.remove(os.path.join(dir, f))

    def write_variable_to_file(self, var, filename, perms):
        f = open(filename, 'w' )
        f.write(var + '\n')
        f.close()
        os.system('chmod ' + perms + ' ' + filename)

    def print_key(self, file, type):
        with open(file,"rb") as f:
           contents = f.read().replace(b"\n",b"\\n")
        keystr = contents.decode("utf-8").replace("b'","'")
        if type == 'private':
            print('"PRIVATEKEY": "' + keystr + '",')
        else:
            print('"PUBLICKEY": "' + keystr + '"')

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
