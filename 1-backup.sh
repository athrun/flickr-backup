#!/bin/sh

export FLICKR_TOKEN_DIR=/volume1/flickr_backup/tokens/
./offlickr.py -s -d sets -i  52574705@N00
./offlickr.py -p -n -d content -i 52574705@N00
