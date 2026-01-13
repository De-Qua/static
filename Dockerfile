FROM continuumio/miniconda3:latest

# Install system dependencies for cron and Shapely
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    libgeos-dev \
    libpq-dev \
    gcc \
    wget \
    ca-certificates \
    libgtk-3-0 \
    && rm -rf /var/lib/apt/lists/*


# Set working directory
WORKDIR /app

# Copy requirements and install
# COPY requirements.txt .
# RUN pip install --no-cache-dir -r requirements.txt

COPY environment.yml .

RUN conda env create -n env -f environment.yml
RUN echo "source activate env" > ~/.bashrc
ENV PATH /opt/conda/envs/env/bin:$PATH

# # Switch to non-root user
# USER appuser

CMD tail -f /dev/null

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

