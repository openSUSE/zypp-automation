# Github_PR interactions (filter and action classes)
require "open-uri"

module GithubPR
  class JenkinsJobTriggerAction < RunCommandAction
	  JENKINS_URL="https://ci.opensuse.org"

    def logging?
      @c.has_key?("detail_logging") && @c["detail_logging"]
    end

    def action(pull)
      if logging? then
        LogPullRequestDetailsAction.new(@metadata).run([pull])
      end
      base_cmd = command("job_cmd")
      job_parameters(pull).each do |build_mode, job_paras|
        one_cmd = base_cmd + [@c["job_name"]] + parameters_to_cmd_paras(job_paras)
	puts "Executing #{one_cmd}"
        system(*one_cmd) or raise
        if logging? then
          puts "  Triggered jenkins job in mode: #{build_mode}"
          puts "  Rebuild Link: #{JENKINS_URL}/job/#{@c["job_name"]}/parambuild/?#{parameters_to_uri(job_paras)}"
          puts "  => NOTE: Job already triggered. Make sure there are no identical parallel jobs!"
        end
      end
    end

    def parameters_to_cmd_paras(paras)
      paras.map{ |k,v| "#{k}=#{v}" }
    end

    def parameters_to_uri(paras)
      URI.encode_www_form(paras)
    end

    def job_parameters(pull)
      @c["job_parameters"].map do |build_mode, build_paras|
        job_paras = build_paras
        if self.respond_to?(:extra_parameters) then
          job_paras.merge!(extra_parameters(pull, build_mode))
        end
        [ build_mode, job_paras ]
      end.to_h
    end
  end

  class JenkinsJobTriggerPRAction < JenkinsJobTriggerAction
    def extra_parameters(pull, build_mode = "")
      job_base_name = "#{@metadata[:repository]} PR #{pull.number} #{pull.head.sha[0,8]}"
      github_pr_base = "#{@metadata[:organization]}:#{@metadata[:repository]}:#{pull.base.ref}:#{pull.number}:#{pull.head.repo.full_name}:#{pull.head.sha}"
      sub_context = build_mode == "standard" ? "":build_mode
      sub_context_suffix = sub_context.empty? ? "" : ":#{sub_context}"
      {
        "job_name" => "#{job_base_name} #{sub_context}",
        "github_pr" => "#{github_pr_base}#{sub_context_suffix}"
      }
    end
  end

  class SetNotTrustedStatusAction < Action
    def action(pull)

      details = { 
          "status" => "failure",
          "message" => "Not a valid CI user, please ask a project contributor to trigger your build via #{JENKINS_URL}/job/#{@c["job_name"]}/parambuild/?#{parameters_to_uri(job_paras)}",
          "target_url" => @c['target_url']
      }

      GithubClient.new(@metadata).create_status(pull.head.sha, @c)
    end
  end

end
