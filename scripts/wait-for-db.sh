#!/bin/bash
#

CURDIR=$(dirname $0)
python $CURDIR/wait_for_rethinkdb.py && "$@"
