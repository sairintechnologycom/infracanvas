FROM python:3.12-slim

WORKDIR /workspace

RUN pip install infracanvas==0.1.0

ENTRYPOINT ["infracanvas"]
CMD ["--help"]
