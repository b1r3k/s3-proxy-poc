# S3 proxy

This is proof of concept.
The idea is to setup HTTP proxy between S3 client (e.g. boto)  and S3 compatible server and perform protocol specific modifications on the fly, for example custom authorization. It's different approach than in https://github.com/jcomo/s3-proxy and https://github.com/pottava/aws-s3-proxy because it's capable of handling all requests made by the client without using AWS SDK - it aims to be transparent for the S3 client.


## How to start

1. `make install`
2. `make run-proxy` in order to start proxy server. Define environment variables in `.env` file.

## How to build production ready docker image

    $ make build-docker-image

In order to publish image to the ECR put ECR_REPO_URI variable pointing to ECR in `.env.build` and run:

    $ poetry run dotenv -e .env.build make publish-docker-image

## Running e2e tests

It uses docker compose to launch s3proxy and [zenko/cloudserver - Docker Image | Docker Hub](https://hub.docker.com/r/zenko/cloudserver) as s3 server and then runs `./tests/e2e` against them.

    $ make e2e-test
