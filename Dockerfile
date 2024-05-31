# syntax=docker/dockerfile:labs

# Dockerfile for PetalVault using multi-stage build
# Use buildkit syntax labs
# https://github.com/moby/buildkit

# I COULD NOT CONFIGURE THIS TO PROPERLY BUILD ARM64 AND AMD64 (so it's just a dummy file for now)

FROM python:3.12-slim AS build

# Install build dependencies
RUN --mount=type=cache,target=/root/.cache/pip \
    apt-get update && apt-get install -y \
    git \
    binutils \
    build-essential \
    python3 \
    python3-venv \
    python3-pip \
    ffmpeg \
    dconf-editor \
    libglib2.0-bin \
    libsm6 \
    libxext6 \
    libegl1 \
    libgl1-mesa-dri \
    libxcb1 \
    libxcb-cursor-dev \
    libgl1-mesa-dev \
    libxkbcommon-x11-0 \
    libxcb-icccm4 \
    libxcb-image0 \
    libxcb-keysyms1 \
    libxcb-randr0 \
    libxcb-render-util0 \
    libxcb-xinerama0 \
    libxcb-xinput0 \
    libxcb-xfixes0 \
    libxcb-shape0 \
    libxcb-render0 \
    libxcb-glx0 \
    libxi6 \
    libxkbfile1 \
    libxcb-cursor0 \
    libgtk-3-0 \
    libatk1.0-0 \
    libglu1 \
    libglu1-mesa \
    freeglut3-dev \
    libglut3.* \
    && pip install pyinstaller

# Verify gsettings installation
RUN gsettings --version

# Copy all graphic libs to fix "ImportError: libGL.so.1: cannot open shared object file: No such file or directory"
RUN find / -name 'libGL*' -exec cp -pv {} /usr/lib/ \; -exec ldconfig -n -v /usr/lib \;
RUN find / -name 'libEGL*' -exec cp -pv {} /usr/lib/ \; -exec ldconfig -n -v /usr/lib \;
RUN find / -name 'libx*' -exec cp -pv {} /usr/lib/ \; -exec ldconfig -n -v /usr/lib \;
RUN find / -name 'libg*' -exec cp -pv {} /usr/lib/ \; -exec ldconfig -n -v /usr/lib \;

# Install PetalVault dependencies
RUN --mount=type=cache,target=/root/.cache/pip \
    --mount=type=bind,source=requirements.txt,target=requirements.txt \
    pip install --upgrade -r requirements.txt

# Build
WORKDIR /src
COPY . /src/
ENV AM_I_IN_A_DOCKER_CONTAINER Yes
RUN pyinstaller /src/main.spec

# Link image
FROM alpine
ENV PATH /app:$PATH

COPY --link --from=python:3.12-slim /li[b] /lib
COPY --link --from=python:3.12-slim /lib6[4] /lib64
COPY --link --from=build /app/dist/petalvault-* /app/petalvault

WORKDIR /app

# Copy internal files (just in case)
COPY forms/ icons/ langs/ wordlist.txt /app/

# Run main script
CMD ["petalvault"]
