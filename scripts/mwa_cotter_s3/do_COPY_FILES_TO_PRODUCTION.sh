#!/bin/bash

obs=$1
pwd=$(pwd)

# Only commenting this out and hardcoding a host because eor-14 is out of space on /r1
#hostname=$(hostname -s)
hostname='eor-13'

production_dir=$(echo $production_dir | sed s/{hostname}/$hostname/)


real_prod_dir=$(echo $production_dir | cut -f 2 -d '/' --complement)

# Only commenting this out and hardcoding a host because eor-14 is out of space on /r1
#if [ ! -d $real_prod_dir ]; then
#   echo "Creating directory : $real_prod_dir"
#   mkdir -p $real_prod_dir
#  if [ $? -ne 0 ]; do
#    echo "Mkdir -p $real_prod_dir failed"
#    exit 1
#  fi
#fi

if [ ! $1 ]; then
   echo "No observation ID given."
   exit 1
fi

if [ ! -d $obs ]; then
   echo "Obs working dir : $pwd/$obs does not exist!"
   exit 1
fi
cd $obs

LIST_OF_FILES="uvfits metafits qs"

for file_type in $LIST_OF_FILES; do
   if [ -e $obs.$file_type ]; then
       aws s3 cp $obs.$file_type s3://mwapublic/uvfits/5.2/$obs.$file_type --profile 21cmdata
       return_code=$?
       if [ $return_code -ne 0 ]; then
           echo "aws s3 cp $obs.$file_type s3://mwapublic/uvfits/5.2/$obs.$file_type --profile 21cmdata experienced a problem"
           exit 1
       fi
   fi
done
exit 0
       
