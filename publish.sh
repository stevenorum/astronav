#!/bin/bash

rm -rf src/sneks
cp -r ../sneks/src/sneks src/

sneks publish-sam-stack
rm -rf src/sneks
