# syntax=docker/dockerfile:labs

# Dockerfile for PetalVault using multi-stage build
# Use buildkit syntax labs
# https://github.com/moby/buildkit

FROM python:3.12-slim AS build
RUN --mount=type=cache,target=/root/.cache/pip \
    apt-get update && \
    apt-get install -y git binutils build-essential qt6-base-dev qt6-tools-dev && \
    pip install pyinstaller

# Install dependencies
RUN --mount=type=cache,target=/root/.cache/pip \
    --mount=type=bind,source=requirements.txt,target=requirements.txt \
    pip install -r requirements.txt

# Build
WORKDIR /src
COPY . /src/
ENV AM_I_IN_A_DOCKER_CONTAINER Yes
RUN pyinstaller /src/main.spec

# Build application image
FROM alpine
ENV PATH /app:$PATH

COPY --link --from=python:3.12-slim /li[b] /lib
COPY --link --from=python:3.12-slim /lib6[4] /lib64
COPY --link --from=build /app/dist/petalvault-* /app/petalvault

WORKDIR /app
COPY forms/ icons/ langs/ /app/

# Run main script
CMD ["petalvault"]
