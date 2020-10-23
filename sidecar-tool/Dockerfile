FROM python

WORKDIR /src

ADD requirements.txt /src

RUN pip install -r requirements.txt

ADD ./src/*.py /src/

CMD python init.py