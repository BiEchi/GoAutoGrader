#!/bin/bash
netid=ziyanga2
mp=mp2
dir=/home/INTL/wenqing.17/code/autograder/tmp/outputreplay
target=/home/INTL/wenqing.17/code/autograder/assets/$netid/mp/$mp/$mp.asm
cd /home/klc3/klc3/examples/mp2
mkdir -p $dir
rm -rf  $dir/*
echo "output in $dir"
echo "grading target: $target"
/bin/env LD_LIBRARY_PATH=/opt/rh/llvm-toolset-7.0/root/usr/lib64 /usr/bin/python3 test.py --output-dir=$dir --regression-dir=/home/INTL/wenqing.17/code/autograder/assets/klc3Storage/$netid/$mp $target 
