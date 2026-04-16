FROM python:3.12-slim AS builder

WORKDIR /app
COPY cli/ ./cli/
COPY viewer/dist/ ./viewer/dist/

RUN pip install --no-cache-dir ./cli

FROM python:3.12-slim

WORKDIR /app
COPY --from=builder /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=builder /usr/local/bin/infracanvas /usr/local/bin/infracanvas

# Include viewer template for HTML export
COPY --from=builder /app/viewer/dist/ /app/viewer/dist/

# Non-root user for security
RUN useradd -m -s /bin/bash infracanvas
USER infracanvas

ENTRYPOINT ["infracanvas"]
CMD ["--help"]

HEALTHCHECK --interval=30s --timeout=3s \
  CMD infracanvas --version || exit 1

LABEL org.opencontainers.image.title="InfraCanvas" \
      org.opencontainers.image.description="Interactive Terraform architecture diagrams" \
      org.opencontainers.image.source="https://github.com/infracanvas/infracanvas" \
      org.opencontainers.image.licenses="MIT"
