#!/bin/sh
#
# Created:      2024-08-11 23:26:05
set -eu

DIR=$(jq -r ".layer.directory" settings.json)
NAME=$(jq -r ".layer.name" settings.json)
S3_BUCKET=$(jq -r ".S3.bucket" settings.json)
S3_KEY=$(jq -r ".S3.key" settings.json)
aws s3 sync build/static/css s3://$S3_BUCKET/$S3_KEY/integration/static/css --delete
aws s3 sync build/static/js s3://$S3_BUCKET/$S3_KEY/integration/static/js --delete
