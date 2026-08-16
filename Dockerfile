# syntax=docker/dockerfile:1
FROM envoyproxy/envoy:v1.32-latest

COPY envoy.yaml /etc/envoy/envoy.yaml

EXPOSE 50051

CMD ["/usr/local/bin/envoy", "-c", "/etc/envoy/envoy.yaml", "--log-level", "info"]
