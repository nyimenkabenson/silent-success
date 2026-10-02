# Two images from one Dockerfile. WITH_PROBE=0 produces an image where the
# probe binary is simply not on PATH - a Dockerfile that did not rebuild, a
# cached layer, a base image that changed. The checker still invokes it.
FROM python:3.12-alpine
ARG WITH_PROBE=1
COPY targets.py /usr/local/bin/targets.py
COPY probe.py /tmp/probe.py
RUN if [ "$WITH_PROBE" = "1" ]; then install -m 755 /tmp/probe.py /usr/local/bin/probe; fi \
    && rm -f /tmp/probe.py
CMD ["python", "/usr/local/bin/targets.py"]
