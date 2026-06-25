#!/bin/bash

# USAGE: .zip_directory.sh

# reinstall rdmt-spire to get latest version
mkdir tmp-pip-dir
pip install -e . --no-dependencies --no-cache-dir --target tmp-pip-dir --quiet
PACKAGE_VERSION=$(pip show rdmt-spire | grep Version | awk '{print $2}')
echo "PACKAGE_VERSION=$PACKAGE_VERSION" > version.env
chmod +x version.env

# clean up the temporary installation
rm -r tmp-pip-dir

# move out a directory and clean any old zip files
cd ..
rm rdmt-spire-4-aws.zip
rm rdmt-spire-4-aws-alembic.zip

# Create the zip archive
zip -r -q rdmt-spire-4-aws.zip rdmt-spire -x "rdmt-spire/.git/*" "rdmt-spire/.github/*" "rdmt-spire/.pytest_cache/*" "rdmt-spire/.ruff_cache/*" "rdmt-spire/build/*" "rdmt-spire/pyarrow_testing/*" "rdmt-spire/rdmt_spire.egg-info/*" "rdmt-spire/sql_layer/*"

unzip -q rdmt-spire-4-aws.zip -d rdmt-spire-4-aws

mv rdmt-spire-4-aws/rdmt-spire/alembic.Dockerfile rdmt-spire-4-aws/rdmt-spire/Dockerfile

cd rdmt-spire-4-aws
zip -r -q ../rdmt-spire-4-aws-alembic.zip rdmt-spire
cd ..

# clean up the version.env file so it isn't version controlled
rm rdmt-spire/version.env
rm -r rdmt-spire-4-aws