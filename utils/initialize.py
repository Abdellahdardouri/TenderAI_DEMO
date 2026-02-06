"""
Global initialization for the TenderAI application.
This module should be imported at the start of the application to set up
the environment, configure warnings, and initialize settings.
"""

import os
import warnings
import logging
from transformers import logging as transformers_logging

# Set environment variables
LLAMA_PARSE_API_KEY = "llx-3WoEmFJuB5IiDlxPm5VX2o27n82gf9gIt9dz3NbQiFMq2zqa"
os.environ["LLAMA_CLOUD_API_KEY"] = LLAMA_PARSE_API_KEY

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Suppress specific warnings
warnings.filterwarnings("ignore", message=".*XLMRobertaTokenizerFast.*")
warnings.filterwarnings("ignore", message=".*tokenizer.*")
warnings.filterwarnings("ignore", message=".*faster to encode.*")
warnings.filterwarnings("ignore", message=".*cuda.*")

# Set transformers logging level to ERROR to hide most warnings
transformers_logging.set_verbosity_error()

# Initialize required directories
for directory in ["data", "data/uploads", "data/md", "output", "static"]:
    os.makedirs(directory, exist_ok=True)

# Print initialization message
print("TenderAI initialization complete")