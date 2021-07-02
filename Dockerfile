FROM python:3.7

ARG VERSION_TAG=latest

ENV VERSION_TAG=${VERSION_TAG}

WORKDIR /src

ADD requirements.txt /src

RUN pip install --no-cache-dir -r requirements.txt

ADD entrypoint.sh /

ADD ./src/*.py /src/

CMD /entrypoint.sh