import os

COLAB_TCP_HOST = os.getenv("COLAB_TCP_HOST", "localhost")
COLAB_TCP_PORT = int(os.getenv("COLAB_TCP_PORT", "9999"))
