#!/bin/sh

HOST="$1"

if [ ! $HOST ]; then
        HOST=on6test
fi

set -e
rsync -av --delete --exclude '*.pyc' opennode/cli/actions/ root@${HOST}:/usr/lib/python2.6/site-packages/salt/modules/onode/
rsync -av --delete --exclude '*.pyc' opennode/ root@${HOST}:/usr/lib/python2.6/site-packages/opennode/
rsync -av --delete --exclude '*.pyc' scripts/ root@${HOST}:opennode/

ssh root@${HOST} service salt-minion restart

