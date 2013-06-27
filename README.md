# About this fork

This is a hacky fork that intends to infer the following information about method calls:

   * className, constructor parameters, method invocation parameters
   * instead of infering type, it would infer object states
   * we would infer only string constants;
   
Of course, there is no way to infer strings that are provided as input parameters.

We need only information about variables/parameters that can only have a predefined set of states.

Sounds ambitious.

Here's a less ambitious goal:
   
    * find "live" code, i.e. all lines of code that could possibly be executed after running script (all branches are evaluated)
    * after that we can easily "grep" these lines for our constants set


# Original README



This is a prototype implementation of the PySonar static analyzer for
Python. It has a similar structure as the one I made at Google, but
has a very preliminary status. It is also somewhat simpler and nicer
designed. It has only the core parts (variables, assignments,
functions and calls), but lacks many important things such as objects,
modules etc.

You can find an introduction to the original Google version at:

http://yinwang0.wordpress.com/2010/09/12/pysonar

I currently have no motivation of developing PySonar further. The
purpose of putting this code here is hoping it can be helpful to
people who want to develop static analysis tools for dynamic
languages.


* Copyright (BSD-style)

Copyright (c) 2012 Yin Wang
All rights reserved.

Redistribution and use in source and binary forms, with or without
modification, are permitted provided that the following conditions
are met:

1. Redistributions of source code must retain the above copyright
   notice, this list of conditions and the following disclaimer.
2. Redistributions in binary form must reproduce the above copyright
   notice, this list of conditions and the following disclaimer in the
   documentation and/or other materials provided with the distribution.
3. The name of the author may not be used to endorse or promote products
   derived from this software without specific prior written permission.

THIS SOFTWARE IS PROVIDED BY THE AUTHOR ``AS IS'' AND ANY EXPRESS OR
IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES
OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE DISCLAIMED.
IN NO EVENT SHALL THE AUTHOR BE LIABLE FOR ANY DIRECT, INDIRECT,
INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT
NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
(INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF
THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
