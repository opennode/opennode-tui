#!/bin/sh

sudo rsync -av --delete modules/opennode/ /usr/local/lib/python2.7/dist-packages/func/minion/modules/opennode/
rsync -av --delete modules/opennode/ root@on6test:/usr/lib/python2.6/site-packages/func/minion/modules/opennode/
