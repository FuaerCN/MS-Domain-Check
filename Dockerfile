FROM python:alpine

ENV TZ Asia/Shanghai

WORKDIR /app

COPY . ./

RUN apk update \
    && apk add --no-cache tor \
	&& echo "SOCKSPort 9150" >> /etc/tor/torrc \
	&& echo "ControlPort 9151" >> /etc/tor/torrc \
	&& pip install stem pysocks requests flask faker

CMD [ "python", "main.py" ]
