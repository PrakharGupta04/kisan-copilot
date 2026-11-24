FROM python:3.11-slim
ENV PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1 PIP_DISABLE_PIP_VERSION_CHECK=1
RUN useradd -m -u 1000 user
WORKDIR /home/user/app
RUN python -m venv /opt/venv-crew && python -m venv /opt/venv-adk
COPY requirements.txt requirements-obs.txt requirements-adk.txt requirements-obs-adk.txt ./
RUN /opt/venv-crew/bin/pip install -r requirements.txt
RUN /opt/venv-adk/bin/pip install -r requirements-adk.txt
RUN /opt/venv-crew/bin/pip install -r requirements-obs.txt || echo "optional obs packages skipped (crew)"
RUN /opt/venv-adk/bin/pip install -r requirements-obs-adk.txt || echo "optional obs packages skipped (adk)"
COPY --chown=user:user . .
RUN mkdir -p data logs && chown -R user:user /home/user/app/data /home/user/app/logs
USER user
ENV VENV_CREW=/opt/venv-crew VENV_ADK=/opt/venv-adk PYTHONPATH=/home/user/app
EXPOSE 7860
CMD ["bash", "start.sh"]
