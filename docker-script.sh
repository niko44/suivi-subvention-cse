#!/bin/bash

docker stop suivi-subvention-cse
docker rm suivi-subvention-cse
docker build -t suivi-subvention-cse .
docker run -d -p 5100:5100 --name suivi-subvention-cse  -v /volume3/docker/cse/upload:/app/upload -v /volume3/docker/cse/bdd:/app/bdd suivi-subvention-cse
