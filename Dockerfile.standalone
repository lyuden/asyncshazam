FROM ubuntu:18.04

ENV DEBIAN_FRONTEND noninteractive

RUN apt-get update && apt-get install -y \
    python3 \
    python3-setuptools \
    python3-pip \
    python3-venv

RUN mkdir /asyncshazam/
RUN mkdir /asyncshazam/web/
RUN python3 -m venv /asyncshazam/venv/

COPY requirements.txt /asyncshazam/
RUN /asyncshazam/venv/bin/pip install --upgrade pip
RUN /asyncshazam/venv/bin/pip install -r /asyncshazam/requirements.txt

COPY web/server.py /asyncshazam/web/

WORKDIR /asyncshazam/

ENV PUBLIC_API_KEY public
ENV PRIVATE_API_KEY private

EXPOSE 8080

CMD ["./venv/bin/python","web/server.py"]



