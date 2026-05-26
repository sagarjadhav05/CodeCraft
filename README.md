# 🛠️ CodeCraft: Multi-Agent AI Flutter Compiler

An autonomous, cloud-hosted Generative AI engine that takes natural language app ideas, writes Dart code via a multi-agent LLM pipeline, and compiles live Flutter Web applications inside a sandboxed Docker container.

## 🧠 Architecture Overview

This project bypasses standard zero-shot code generation by implementing an Agentic Pipeline. It does not just write code; it plans, writes, stitches, and compiles in a closed-loop environment.

1. **The Planner Agent:** Acts as the Software Architect. Takes the user's raw idea and drafts a strict, bulleted technical blueprint, explicitly filtering out hallucinated packages or complex state management.
2. **The Maker Agent:** Acts as the Developer. Writes strict, null-safe Dart code locked into a single-file `GeneratedAppBody` widget based entirely on the Planner's blueprint.
3. **The Stitcher (Python Orchestrator):** Intercepts the raw LLM output, extracts `import` statements to prevent directive errors, and cleanly injects the UI code into a pre-configured `main.dart` template.
4. **The Sandbox Engine:** A dynamic Docker environment that creates Flutter projects on the fly, executes the Dart-to-Wasm/JS compiler, and returns either a live `iframe` of the app or the exact terminal crash logs for debugging.

## 🚀 Tech Stack

* **LLM Engine:** Llama 3 (70B Versatile) via Groq API for near-instant inference.
* **Backend Orchestration:** Python, FastAPI, and Gradio for the agentic loop and UI.
* **Compiler Environment:** Custom Docker image (Ubuntu 22.04) running the stable Flutter Web SDK.
* **Hosting:** Hugging Face Spaces.

## ⚡ Engineering Challenges Solved

Building a live compiler in the cloud requires overcoming strict container restrictions. Key infrastructure problems solved in this repository include:

* **Dynamic Subprocess Pathing:** Overcoming Python `subprocess` environment stripping by engineering absolute path injectors and raw shell (`shell=True`) commands to locate the Flutter binary.
* **Docker Privilege Boundaries:** Flutter strictly refuses to install or compile as a `root` user. The Dockerfile was custom-engineered to create localized users and manipulate `$HOME` pathing to securely cache the Web SDK.
* **FastAPI Asynchronous Routing:** Fixed the standard "Base Href" routing bugs by mounting FastAPI static files dynamically to `/preview` and injecting `--base-href /preview/` directly into the Flutter build command so the rendered JS engines route correctly inside Hugging Face iframes.
* **LLM Hallucination Mitigation:** Implemented One-Shot Prompting and strict structural straightjackets to prevent the AI from hallucinating multi-file architectures or unauthorized external HTTP packages.

## 💻 Running Locally

1. Clone the repository: `git clone https://github.com/YOUR_USERNAME/CodeCraft.git`
2. Ensure Docker is installed on your machine.
3. Build the container: `docker build -t codecraft .`
4. Run the container, passing your Groq API key:
   `docker run -p 7860:7860 -e GROQ_API_KEY="your_key_here" codecraft`
5. Open `http://localhost:7860` in your browser.
