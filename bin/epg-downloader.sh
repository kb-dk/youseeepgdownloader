#!/bin/bash
cd $(dirname $(dirname $(readlink -f $0 ) ) )
lib/yousee-epg-downloader.py conf/epg-config.json
