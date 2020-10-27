FROM python:3.7

WORKDIR /src

ADD requirements.txt /src

RUN pip install --no-cache-dir -r requirements.txt

ADD ./src/*.py /src/

CMD kopf run init.py --verbose