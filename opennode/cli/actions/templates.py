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
