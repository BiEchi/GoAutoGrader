# Queue System for KLC3

## Install
```shell
# establish the working environment
yum install git, go
git clone https://github.com/BiEchi/GoAutoGrader

# if the server is running in China, you need to include this line to set the netwrok 
go env -w GOPROXY=https://goproxy.cn

# build the source code (all dependencies will be downloaded automatically)
go build -o queue

# run the program and start watching
./queue
```

## License

University of Illinois/NCSA Open Source License

Copyright (c) 2020-2021 Wenqing Luo. All rights reserved.

Developed by: Wenqing Luo
              University of Illinois at Urbana-Champaign

Permission is hereby granted, free of charge, to any person
obtaining a copy of this software and associated documentation files
(the "Software"), to deal with the Software without restriction,
including without limitation the rights to use, copy, modify, merge,
publish, distribute, sublicense, and/or sell copies of the Software,
and to permit persons to whom the Software is furnished to do so,
subject to the following conditions:

* Redistributions of source code must retain the above copyright notice,
  this list of conditions and the following disclaimers.

* Redistributions in binary form must reproduce the above copyright
  notice, this list of conditions and the following disclaimers in the
  documentation and/or other materials provided with the distribution.

* Neither the names of University of Illinois at Urbana-Champaign nor the 
  names of its contributors may be used to endorse or promote products derived 
  from this Software without specific prior written permission.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS
OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
CONTRIBUTORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS WITH
THE SOFTWARE.