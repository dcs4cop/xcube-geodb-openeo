FROM continuumio/miniconda3:4.12.0

LABEL maintainer="xcube-team@brockmann-consult.de"
LABEL name=xcube_geodb_openeo

RUN conda install -n base -c conda-forge mamba pip

#ADD environment.yml /tmp/environment.yml
ADD . /tmp/
WORKDIR /tmp
RUN mamba env update -n base
RUN . activate base

RUN git clone https://github.com/dcs4cop/xcube.git
WORKDIR /tmp/xcube
RUN git checkout forman-676-server_redesign
RUN mamba env update -n base
RUN pip install -e .

WORKDIR /tmp/
RUN pip install -e .

CMD ["xcube", "--loglevel=DETAIL", "--traceback", "serve2", "-vvv", "-c", "/etc/config/config.yml"]