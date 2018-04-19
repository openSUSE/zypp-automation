SHELL := /bin/bash
test: filecheck bashate perlcheck rubycheck pythoncheck rounduptest flake8 python_unittest jjb_test

clean:
	rm -f scripts/jenkins/jenkins-job-triggerc scripts/lib/libvirt/{net-configc,vm-startc,compute-configc,net-startc,admin-configc,cleanupc}
	find -name \*.pyc -print0 | xargs -0 rm -f

filecheck:
	! git ls-tree -r HEAD --name-only | \
		egrep -v 'Makefile|sample-logs/.*\.txt$$' | \
		xargs grep $$'\t'

bashate:
	cd scripts && \
	for f in \
	    *.sh mkcloud mkchroot repochecker \
	    jenkins/{update_automation,*.sh} \
	    ../hostscripts/ci1/* ../hostscripts/clouddata/syncSLErepos ../mkcloudruns/*/[^R]*;\
	do \
	    echo "checking $$f"; \
	    bash -n $$f || exit 3; \
	    bashate --ignore E006,E010,E011,E020,E042 $$f || exit 4; \
	    ! grep $$'\t' $$f || exit 5; \
	done

perlcheck:
	cd scripts && \
	for f in `find -name \*.pl` jenkins/{apicheck,grep,japi} mkcloudhost/allocpool ; \
	do \
	    perl -wc $$f || exit 2; \
	done

rubycheck:
	for f in `find -name \*.rb` scripts/jenkins/jenkinslog; \
	do \
	    ruby -wc $$f || exit 2; \
	done

pythoncheck:
	for f in `find -name \*.py` scripts/lib/libvirt/{admin-config,cleanup,compute-config,net-config,net-start,vm-start} scripts/jenkins/jenkins-job-trigger; \
        do \
	    python -m py_compile $$f || exit 22; \
	done

rounduptest:
	cd scripts && roundup
	cd scripts/jenkins && roundup

flake8:
	flake8 scripts/ hostscripts/soc-ci/soc-ci

python_unittest:
	python -m unittest discover -v -s scripts/lib/libvirt/

jjb_test:
	jenkins-jobs --conf /etc/jenkins_jobs/jenkins_jobs-cioo.ini --ignore-cache test jenkins:jenkins/ci.opensuse.org:jenkins/ci.opensuse.org/templates/ zypp*  > /dev/null

cioo_deploy:
	jenkins-jobs --conf /etc/jenkins_jobs/jenkins_jobs-cioo.ini update jenkins:jenkins/ci.opensuse.org:jenkins/ci.opensuse.org/templates/ zypp*
