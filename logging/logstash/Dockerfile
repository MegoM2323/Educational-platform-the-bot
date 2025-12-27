# Custom Logstash image for THE_BOT platform
# Includes custom patterns and plugins

FROM docker.elastic.co/logstash/logstash:8.11.0

# Install plugins
RUN logstash-plugin install logstash-filter-json_encode \
    && logstash-plugin install logstash-filter-translate \
    && logstash-plugin install logstash-output-cloudwatch

# Copy custom patterns
COPY patterns /usr/share/logstash/patterns/

# Copy configuration
COPY logstash.conf /usr/share/logstash/pipeline/

# Create log directory
RUN mkdir -p /var/log/logstash && chmod 777 /var/log/logstash

# Set permissions
RUN chown -R logstash:logstash /usr/share/logstash

EXPOSE 5000 5000/udp 9600

CMD ["logstash", "-f", "/usr/share/logstash/pipeline/logstash.conf"]
