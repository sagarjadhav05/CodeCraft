FROM ubuntu:22.04

# 1. Install System Prerequisites (as Root administrator)
RUN apt-get update && apt-get install -y \
    curl git unzip xz-utils zip libglu1-mesa \
    python3 python3-pip python3-venv \
    && rm -rf /var/lib/apt/lists/*

# 2. CREATE THE USER FIRST (Hugging Face Requirement)
RUN useradd -m -u 1000 user
USER user
ENV HOME=/home/user
WORKDIR $HOME/app

# 3. Install Flutter securely as the standard user
RUN git clone https://github.com/flutter/flutter.git -b stable $HOME/flutter
ENV PATH="$HOME/flutter/bin:$PATH"
RUN flutter config --enable-web
RUN flutter precache

# 4. Pre-build a dummy app to cache the Web SDK
RUN flutter create preview_app
WORKDIR $HOME/app/preview_app
RUN flutter build web
WORKDIR $HOME/app

# 5. Install Python Dependencies
COPY --chown=user requirements.txt .
RUN pip3 install --no-cache-dir -r requirements.txt

# 6. Copy Application Code
COPY --chown=user . .

# 7. Expose Port and Run
EXPOSE 7860
CMD ["python3", "app.py"]