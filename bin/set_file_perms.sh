#!/bin/bash

# If not 3 arguments print usage and exit
if [ "$#" -ne 3 ]; then
    echo "Usage: $0 <user> <group> <directory>"
    exit 1
fi

# first argument is the user
USER=$1

# second argument is the group
GROUP=$2

# Third argument is the directory
DATA=$3

# Change owner to dennis:www-data
chown -R $USER:$GROUP $DATA

# Change all dirs to 775
find $DATA -type d -exec chmod 775 {} \;

# Change all files to 664
find $DATA -type f -exec chmod 664 {} \;
