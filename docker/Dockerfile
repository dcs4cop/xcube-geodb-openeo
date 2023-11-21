ARG MICROMAMBA_VERSION=1.3.1
FROM mambaorg/micromamba:${MICROMAMBA_VERSION}

LABEL maintainer="xcube-team@brockmann-consult.de"
LABEL name=xcube_geodb_openeo

ARG NEW_MAMBA_USER=xcube-geodb-openeo
ARG NEW_MAMBA_USER_ID=1000
ARG NEW_MAMBA_USER_GID=1000

# <<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<
USER root

# Update system and ensure that basic commands are available.
RUN apt-get -y update && \
    apt-get -y upgrade vim jq curl wget && \
    apt-get -y install git && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

# Magic taken from https://hub.docker.com/r/mambaorg/micromamba,
# section "Changing the user id or name"
RUN usermod "--login=${NEW_MAMBA_USER}" "--home=/home/${NEW_MAMBA_USER}" \
        --move-home "-u ${NEW_MAMBA_USER_ID}" "${MAMBA_USER}" && \
    groupmod "--new-name=${NEW_MAMBA_USER}" \
             "-g ${NEW_MAMBA_USER_GID}" "${MAMBA_USER}" && \
    # Update the expected value of MAMBA_USER for the
    # _entrypoint.sh consistency check.
    echo "${NEW_MAMBA_USER}" > "/etc/arg_mamba_user" && \
    :

ENV MAMBA_USER=$NEW_MAMBA_USER
# >>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>

USER $MAMBA_USER

COPY --chown=$MAMBA_USER:$MAMBA_USER ../environment.yml /tmp/environment.yml
RUN micromamba install --yes -n base --file /tmp/environment.yml && \
    micromamba clean --all --yes
ARG MAMBA_DOCKERFILE_ACTIVATE=1

RUN micromamba install -n base -c conda-forge pip

ADD docker /tmp/
WORKDIR /tmp

RUN git clone https://github.com/dcs4cop/xcube.git
WORKDIR /tmp/xcube
RUN pip install -e .

WORKDIR /tmp/
RUN git clone https://github.com/dcs4cop/xcube-geodb.git
WORKDIR /tmp/xcube-geodb
RUN pip install -e .

# Copy files for xcube_geodb_openeo source install
COPY --chown=$MAMBA_USER:$MAMBA_USER ../setup.py /tmp/setup.py
COPY --chown=$MAMBA_USER:$MAMBA_USER ../xcube_geodb_openeo /tmp/xcube_geodb_openeo

# Switch into /tmp to install xcube-geodb-openeo
WORKDIR /tmp
RUN python setup.py install

CMD ["python", "-m", "xcube.cli.main", "--loglevel=DETAIL", "--traceback", "serve", "-vvv", "-c", "/etc/config/config.yml"]