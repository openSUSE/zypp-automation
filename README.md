# zypp-automation
CI automation scripts for zypper and libzypp

# bootstrapping:
- Copy jenkinsapi.conf.example to /etc/jenkinsapi.conf , replace the example values with the correct values for the jenkins login
  and API token
- Create a file named /etc/jenkins_jobs/jenkins_jobs-cioo.ini: 
```
[jenkins]
user=my-jenkins-user
password=my-jenkins-pw
url=http://my-jekins-url
query_plugins_info=False     
```
- Create a .netrc file in the build users home directory with the github user/password:
```
machine api.github.com 
        login myuser
        password  mypass
```
- make sure the .netrc file has mode 0600
- check out this repository in a temporary directory
- make sure jenkins-job-builder is installed:  pip install --user 'python-jenkins==0.4.14' 'jenkins-job-builder==1.6.2'
- run make
