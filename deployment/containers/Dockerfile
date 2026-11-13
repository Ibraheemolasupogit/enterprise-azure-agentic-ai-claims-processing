# Inputs are mandatory reviewed content addresses; there is no mutable/default base tag.
ARG PYTHON_BASE
ARG SOURCE_DATE_EPOCH
FROM ${PYTHON_BASE} AS install
ENV PIP_NO_INDEX=1 PIP_DISABLE_PIP_VERSION_CHECK=1 PIP_NO_CACHE_DIR=1 PIP_CONFIG_FILE=/dev/null
COPY artifacts/ /artifacts/
RUN --network=none python -m venv /opt/venv \
    && /opt/venv/bin/python -m pip install --no-index --no-deps --only-binary=:all: \
       --require-hashes -r /artifacts/requirements.txt \
    && /opt/venv/bin/python -m pip check

FROM ${PYTHON_BASE} AS runtime
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PYTHONHASHSEED=0 TZ=UTC \
    PIP_NO_INDEX=1 PIP_DISABLE_PIP_VERSION_CHECK=1 M23_CLOUD_EXECUTION=disabled
COPY --from=install /opt/venv /opt/venv
COPY entrypoint.py smoke.py /app/
COPY fixtures/ /app/fixtures/
WORKDIR /app
USER 10001:10001
EXPOSE 8080
HEALTHCHECK --interval=30s --timeout=3s --retries=3 \
    CMD ["/opt/venv/bin/python", "-I", "-B", "/app/entrypoint.py", "--healthcheck"]
ENTRYPOINT ["/opt/venv/bin/python", "-I", "-B", "/app/entrypoint.py"]
CMD ["--service", "api-ui"]
