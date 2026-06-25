# Made for rdmt
FROM public.ecr.aws/lambda/python:3.12

# Copy rdmt-spire code to Lambda task directory in Docker container
COPY . ${LAMBDA_TASK_ROOT}

# pip install local rdmt-spire code with the correct version
ENV SETUPTOOLS_SCM_PRETEND_VERSION=0
RUN . ${LAMBDA_TASK_ROOT}/version.env && \
    SETUPTOOLS_SCM_PRETEND_VERSION=${PACKAGE_VERSION} && \
    pip3 install . --no-cache-dir --target "${LAMBDA_TASK_ROOT}"

ENV DUCKDB_EXTENSIONS_PATH=/duckdb_extensions
RUN mkdir -p ${DUCKDB_EXTENSIONS_PATH}

# 2. Pre-install DuckDB extensions during the build
# This requires internet access during BUILD TIME, but not at RUN TIME.
RUN python3 -c "import duckdb; \
    con = duckdb.connect(); \
    con.execute(f\"SET extension_directory = '{'${DUCKDB_EXTENSIONS_PATH}'}';\"); \
    con.execute('INSTALL mysql;'); \
    con.execute('INSTALL aws;'); \
    con.execute('INSTALL httpfs;')"

CMD ["rdmt_spire.app.handler"]
