#!/usr/bin/python3

import argparse
import subprocess
import sys
import re
import os

#job trigger:
#env HOME=/var/lib/jenkins  /var/lib/jenkins/github.com/openSUSE/github-pr/github_pr.rb -a trigger-prs --mode rebuild --debugratelimit --config /home/zbenjamin/workspace/zypp-automation/scripts/github_pr/github_pr_zypp.yaml 

debug = False

def getCmakeVar (cmakefile, varname, required=True):
    """
    Tries to query a cmake variable from any cmake file
    """
    # since cmake has no way to only query variables we resort to sed
    # sed -n -E  CMakeLists.txt
    regex = "s/^\\s?[sS][eE][tT]\\s?\\(\\s?{}\\s+\"([^\"]+)\"\\s?\\)\\s?$/\\1/p".format(varname)

    res = None
    try:
        res = subprocess.check_output(["sed", "-n", "-E", regex, cmakefile])
    except subprocess.CalledProcessError:
        print("Failed to read variable {} from cmake file".format(varname), file=sys.stderr)
        sys.exit(1)

    # convert to string and remove whitespace at beginning and end
    result = res.decode() 
    result = result.lstrip()
    result = result.rstrip()

    if required and len(result) == 0:
        print("Could not find required variable: {}".format(varname), file=sys.stderr)
        sys.exit(1)

    return result

def compileVersionString (template):
    """
    A version string template looks like: ${LIBZYPP_MAJOR}.${LIBZYPP_MINOR}.${LIBZYPP_PATCH},
    so we get all variables and replace them from the VERSION.cmake file
    """
    
    verstring = template
    regex = re.compile('\\${([^}]+)}')
    for match in regex.finditer(template):
        varname = match.group(1)
        if debug: print ("Query version file for {}".format(varname))
        val = getCmakeVar("git_src/VERSION.cmake", varname)
        
        if len(val) == 0:
            print("Could not find a value for var {} in VERSION.cmake".format(varname), file=sys.stderr)
            sys.exit(1)

        if debug: print ("Found value: {} for {}".format(val, varname))
        verstring = verstring.replace('${{{}}}'.format(varname), val)

    return verstring

def configureCmakeTemplate (cmakeTempl, vars):
    """
    Replaces all occurrences of @VARNAME@ in the template file with values
    given in the vars dict.
    """
    for key in vars.keys():
        ret = subprocess.call(["sed", "-i", "s/@{}@/{}/".format(key, vars[key]), cmakeTempl] )
        if ret != 0:
            print("Failed to replace variable {} in file {}".format(key, cmakeTempl), file=sys.stderr)
            sys.exit(1)    

def rpmQuery (query, specfile):
    """
    Queries information from the specfile, pass query in rpm QUERYFORMAT
    """
    if debug: print("Executing query {}".format(query))

    res = None
    
    try:
        res = subprocess.check_output(["rpmspec", "-q", "--srpm", "--qf", query, specfile])
    except subprocess.CalledProcessError:
        print("Failed to query spec file", file=sys.stderr)
        sys.exit(1)

    if debug: print("Query result of {}: \"{}\"".format(query, res.decode()))

    return res.decode()

def guessTarballName (specfile):
    """
    Tries to guess the tarball name from the given specfile. The assumption is
    that SOURCE or SOURCE0 will always contain the tarball name. However those can contain variables
    so we try to resolve them by running rpmspec
    """
    #read the tar
    regex = re.compile("^Source[0]{0,1}:\\s+(.*)")
    specfileHndl = open(specfile,"r")
    for line in specfileHndl:
        linematch = regex.match(line)
        if linematch:
            #we found the line we are looking for
            varMatcher = re.compile("%{([^}]*)}")
            source0 = linematch.group(1)
            if debug: print("Matched line: \"{}\"".format(source0))
            compiledSource0 = source0
            for varMatch in varMatcher.finditer(source0):
                varValue = rpmQuery("%{{{}}}".format(varMatch.group(1)), specfile)
                if len(varValue) > 0:
                    compiledSource0 = compiledSource0.replace(varMatch.group(0), varValue)

            print("Tarball Name: {}".format(compiledSource0))
            return compiledSource0
    return None


parser = argparse.ArgumentParser(description='Pull and build a zypp project using its obs counterpart.')
parser.add_argument('githubpr', help='Pull request desc in the form of base_org:base_proj:base_branch:pr_nr:pr_repo:pr_sha')

args = parser.parse_args()

#
conf = args.githubpr.split(":")
base_org    = conf[0]
base_proj   = conf[1]
base_branch = conf[2]
pr_repo     = conf[4]
pr_sha      = conf[5]


#clean up old builds
res = subprocess.call(["bash", "-c" ,"rm -rf git_src obs_src"])
if res != 0:
    print("Failed to read OBS project configuration", file=sys.stderr)
    sys.exit(1)

#osc co -o zypp:Head/package <package>
res = subprocess.call(["osc", "-A", "https://api.opensuse.org", "co", "zypp:Head/{}".format(base_proj), "-o", "obs_src"])
if res != 0:
    print("Failed to read OBS project configuration", file=sys.stderr)
    sys.exit(1)

#git branch ${org_repo} git_src
res = subprocess.call(["git", "clone", "git://github.com/{}/{}".format(base_org, base_proj), "git_src"])
if res != 0:
    print("Failed to clone git project", file=sys.stderr)
    sys.exit(1)

#git checkout target branch
res = subprocess.call(["git", "checkout", base_branch], cwd="git_src")
if res != 0:
    print("Failed to checkout base branch", file=sys.stderr)
    sys.exit(1)

#git remote add PR ${git_pr_repo}
res = subprocess.call(["git", "remote", "add", "PR","git://github.com/{}".format(pr_repo)], cwd="git_src")
if res != 0:
    print("Failed to add the PR remote", file=sys.stderr)
    sys.exit(1)

#git fetch PR ${git_pr_branch}
res = subprocess.call(["git", "fetch", "PR"], cwd="git_src")
if res != 0:
    print("Failed to fetch the PR remote", file=sys.stderr)
    sys.exit(1)

#git merge ${git_pr_sha}
res = subprocess.call(["git", "merge", pr_sha], cwd="git_src")
if res != 0:
    print("Failed to merge the PR", file=sys.stderr)
    sys.exit(1)

#figure out VERSION and PACKAGE
package_str = getCmakeVar("git_src/CMakeLists.txt", "PACKAGE")
print("Package Name: {}".format(package_str))

ver_str = getCmakeVar("git_src/CMakeLists.txt", "VERSION")
ver_str = compileVersionString(ver_str)
print("Package Version: {}".format(ver_str))

#build specfile from spec.cmake
specfile = "obs_src/{}.spec".format(package_str)
res = subprocess.call(["cp", "git_src/{}.spec.cmake".format(package_str), specfile])
if res != 0:
    print("Failed to move spec file", file=sys.stderr)
    sys.exit(1)

configureCmakeTemplate(specfile, {
    "PACKAGE": package_str,
    "VERSION": ver_str 
})

#figure out how to name the source tar
tarfile = guessTarballName(specfile)
srcRootDir = rpmQuery("%{name}-%{version}", specfile)

#tar source using version name
# tar -cjf ../libzypp.tar-bz2 --transform 's,^\.,libzypp,' .
res = subprocess.call(["tar", "cjf", "../obs_src/{}".format(tarfile), "--transform", 's,^\\.,{},'.format(srcRootDir), "--exclude", ".git", '.'], cwd="git_src")
if res != 0:
    print("Failed to tar src dir", file=sys.stderr)
    sys.exit(1)   

#WORKSPACE
buildEnv = os.environ.copy()

jenkinsWorkspace = os.getcwd()
buildRoot    = os.path.join(jenkinsWorkspace, "build-root", "%(repo)s-%(arch)s")
packageCache = os.path.join(jenkinsWorkspace, "pkg-cache")

buildEnv["OSC_BUILD_ROOT"] = buildRoot
buildEnv["OSC_PACKAGECACHEDIR"] = packageCache

#osc build --vm-type=kvm --vm-memory=2000 --clean openSUSE_Tumbleweed
res = subprocess.call(["osc", "-A", "https://api.opensuse.org", "build", "--vm-type=kvm", "--vm-memory=4000", "--clean", "--trust-all-projects" ,"openSUSE_Tumbleweed"], 
                     cwd="obs_src",
                     env=buildEnv
)

if res != 0:
    print("Failed to build PR", file=sys.stderr)
    sys.exit(1)   

#cleanup
sys.exit(0)
