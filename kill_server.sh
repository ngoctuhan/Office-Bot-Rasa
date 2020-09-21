#!/bin/bash

fuser -k 6114/tcp
fuser -k 5014/tcp
cat resources/pid/*.pid | xargs kill -9
rm resources/pid/*.pid
