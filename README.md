# S3 proxy

This is proof of concept.
The idea is to setup HTTP proxy between S3 client (e.g. boto)  and S3 compatible server and perform protocol specific modifications on the fly, for example custom authorization. It's different approach than in https://github.com/jcomo/s3-proxy and https://github.com/pottava/aws-s3-proxy because it's capable of handling all requests made by the client without using AWS SDK - it aims to be transparent for the S3 client.


## How to start

1. `make install`
2. `make run-proxy` in order to start proxy server
5. `make run-client` in order to start boto-based client and perform some operations
