#!/bin/bash
PROTOC=$(which protoc)
if [ ! -x ${PROTOC} ]; then
    echo "error: protocol buffer compiler (protoc) not installed!"
    exit -1
fi

echo Generating protocol buffer wrapper ...
pushd proto 2>/dev/null 1>&2
protoc --python_out=.. backdrop_wallpaper.proto
popd 2>/dev/null 1>&2

