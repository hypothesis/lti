FROM gliderlabs/alpine:3.4
MAINTAINER Hypothes.is Project and contributors

# Install system build and runtime dependencies.
RUN apk-install ca-certificates python py-pip supervisor postgresql-dev

# Create the lti user, group, home directory and package directory.
RUN addgroup -S lti \
  && adduser -S -G lti -h /var/lib/lti lti
WORKDIR /var/lib/lti

COPY requirements.txt ./

RUN pip install --no-cache-dir -U pip \
  && pip install --no-cache-dir -r requirements.txt

COPY . .

# Start the web server by default
EXPOSE 8001
USER lti
CMD ["supervisord", "-c" , "conf/supervisord.conf"]
