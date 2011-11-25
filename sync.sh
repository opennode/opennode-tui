#!/bin/sh

#sudo rsync -av --delete modules/opennode/ /usr/local/lib/python2.7/dist-packages/func/minion/modules/opennode/
sudo chown $USER:$USER -R .
rsync -av --delete --exclude '*.pyc' modules/onode/ root@on6test:/usr/lib/python2.6/site-packages/func/minion/modules/onode/
rsync -av --delete --exclude '*.pyc' opennode/ root@on6test:/usr/lib/python2.6/site-packages/opennode/
