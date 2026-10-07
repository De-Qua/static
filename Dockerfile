FROM condaforge/miniforge3:26.7.2-0

# Install system dependencies for cron and Shapely
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    libgeos-dev \
    libpq-dev \
    build-essential \
    wget \
    ca-certificates \
    libgtk-3-0 \
    tzdata \
    && rm -rf /var/lib/apt/lists/*

# Install supercronic (cron for containers: job output goes to the container logs)
ARG SUPERCRONIC_VERSION=v0.2.49
ARG SUPERCRONIC_SHA256=a53ae236602c7338aba3fbaff40bda6300eae3b9fedb8261eb06cfe3724430c1
RUN wget -q -O /usr/local/bin/supercronic \
    https://github.com/aptible/supercronic/releases/download/${SUPERCRONIC_VERSION}/supercronic-linux-amd64 \
    && echo "${SUPERCRONIC_SHA256}  /usr/local/bin/supercronic" | sha256sum -c - \
    && chmod +x /usr/local/bin/supercronic


# Set working directory
WORKDIR /app

# Copy requirements and install
# COPY requirements.txt .
# RUN pip install --no-cache-dir -r requirements.txt

COPY environment.yml .

RUN mamba env create -n env -f environment.yml && \
    conda clean -afy && \
    find /opt/conda/envs/env -name "*.pyc" -delete && \
    find /opt/conda/envs/env -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null; true

RUN echo "source activate env" > ~/.bashrc
ENV PATH=/opt/conda/envs/env/bin:$PATH
ENV PYTHONUNBUFFERED=1

# # Switch to non-root user
# USER appuser

# Run the scheduled jobs defined in app/crontab (reloaded automatically when the file changes)
CMD ["supercronic", "-inotify", "/app/crontab"]

# ENV PATH="/root/miniconda3/bin:${PATH}"
# ARG PATH="/root/miniconda3/bin:${PATH}"
# RUN wget https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh \
#     && mkdir /root/.conda \
#     && bash Miniconda3-latest-Linux-x86_64.sh -b \
#     && rm -f Miniconda3-latest-Linux-x86_64.sh \
#     && echo "Running $(conda --version)" && \
#     conda init bash && \
#     . /root/.bashrc && \
#     conda update conda && \
#     conda env create --name dequa-static -f environment.yml && \
#     conda activate dequa-static

# RUN echo 'conda activate dequa-static \n'
# alias python-app="python python-app.py"' >> /root/.bashrc
# ENTRYPOINT [ "/bin/bash", "-l", "-c" ]
# CMD ["python python-app.py"]
# CMD tail -f /dev/null

