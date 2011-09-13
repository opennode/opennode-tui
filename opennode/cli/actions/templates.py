import urllib2

from opennode.cli.config import c

def get_template_repos():
    """Return a formatted list of strings describing configured repositories"""
    repo_groups = c('general', 'repo-groups').split(',')
    result = []
    for r in repo_groups:
        group = "%s-repo" % r.strip()
        name = c(group, 'name')
        type = c(group, 'type')
        result.append(("%s (%s)" %(name, type), group))
    return result

def get_template_list(remote_repo):
    """Retrieves a list of templates from the specified repository"""
    url = c(remote_repo, 'url')
    list = urllib2.urlopen("%s/templatelist.txt" % url)
    templates = [template.strip() for template in list]
    list.close()
    return templates

