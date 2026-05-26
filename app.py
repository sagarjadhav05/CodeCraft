import os
import time
import sqlite3
import datetime
import subprocess
import gradio as gr
from groq import Groq
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

# ─────────────────────────────────────────────────────────────────
# CONFIGURATION & FLUTTER PATHS
# ─────────────────────────────────────────────────────────────────
MODEL = "llama-3.3-70b-versatile"
DB_PATH = "codecraft_memory.db"
FLUTTER_PROJECT_DIR = "/home/user/app/preview_app"
FLUTTER_MAIN_FILE = f"{FLUTTER_PROJECT_DIR}/lib/main.dart"

# ─────────────────────────────────────────────────────────────────
# DB & FLUTTER HELPERS
# ─────────────────────────────────────────────────────────────────
def init_db():
    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()
    cur.execute('''CREATE TABLE IF NOT EXISTS projects 
                   (id INTEGER PRIMARY KEY AUTOINCREMENT, prompt TEXT, code TEXT, timestamp TEXT)''')
    con.commit()
    con.close()

def save_to_memory(prompt: str, code: str) -> int:
    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()
    cur.execute("INSERT INTO projects (prompt, code, timestamp) VALUES (?, ?, ?)",
                (prompt, code, datetime.datetime.utcnow().isoformat()))
    project_id = cur.lastrowid
    con.commit()
    con.close()
    return project_id

BASE_IMPORTS = "import 'package:flutter/material.dart';\nimport 'dart:math';\n"
BASE_MAIN = """
void main() { runApp(const MyApp()); }
class MyApp extends StatelessWidget {
  const MyApp({super.key});
  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      debugShowCheckedModeBanner: false,
      theme: ThemeData(colorScheme: ColorScheme.fromSeed(seedColor: Colors.deepPurple), useMaterial3: true),
      home: GeneratedAppBody(),
    );
  }
}
"""

def _llm(system: str, user: str, temp: float = 0.7) -> str:
    """Bulletproof API Call with dynamic temperature annealing."""
    api_key = os.environ.get("GROQ_API_KEY", "").strip()
    if not api_key:
        raise gr.Error("Fatal API Error: GROQ_API_KEY is missing.")
        
    client = Groq(api_key=api_key)
    max_retries = 3
    for attempt in range(max_retries):
        try:
            response = client.chat.completions.create(
                model=MODEL, 
                temperature=temp,
                messages=[{"role": "system", "content": system}, {"role": "user", "content": user}]
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            if attempt == max_retries - 1:
                raise gr.Error(f"API Network Error (Attempt {attempt+1}/3): {str(e)}")
            time.sleep(2)

def compile_to_web(final_code: str):
    """Dynamically locates the Flutter binary and compiles the app with the correct base href."""
    import shutil
    
    flutter_bin = shutil.which("flutter") or "/home/user/flutter/bin/flutter"
    
    try:
        os.makedirs(os.path.dirname(FLUTTER_MAIN_FILE), exist_ok=True)
        
        with open(FLUTTER_MAIN_FILE, "w") as f:
            f.write(final_code)
            
        if not os.path.exists(f"{FLUTTER_PROJECT_DIR}/pubspec.yaml"):
            subprocess.run(
                f"{flutter_bin} create preview_app", 
                shell=True,
                cwd="/home/user/app", 
                capture_output=True
            )
        
        # FIX: Added --base-href /preview/ so the app knows where its Javascript files live
        result = subprocess.run(
            f"{flutter_bin} build web --release --base-href /preview/",
            shell=True,
            cwd=FLUTTER_PROJECT_DIR,
            capture_output=True,
            text=True
        )
        
        if result.returncode == 0:
            return True, "Success"
        else:
            return False, result.stderr or result.stdout
            
    except Exception as e:
        return False, f"System Error executing Flutter at {flutter_bin}: {str(e)}"

# ─────────────────────────────────────────────────────────────────
# THE PIPELINE (WITH SELF-HEALING CRITIC)
# ─────────────────────────────────────────────────────────────────
def autonomous_agentic_loop(app_idea: str):
    placeholder = "<div style='height:600px; border:2px dashed #4ade80; display:flex; align-items:center; justify-content:center; border-radius:8px; color:#4ade80; font-family:monospace; background:#0d1117;'>[ Live App Preview Will Render Here ]</div>"

    if not app_idea.strip():
        yield "❌ Enter an app idea.", "", placeholder
        return

    # 1. Planner (Only runs once)
    yield "🧠 [Planner] Designing blueprint...", "", placeholder
    planner_sys = "You are a UI Designer. Output a simple, static visual layout plan. NO logic, NO data models, NO custom classes. Target widget: GeneratedAppBody."
    blueprint = _llm(planner_sys, f"App idea: {app_idea}\nProduce blueprint.")
    
    # 2. Maker Base System (The unbreakable rules)
    maker_sys = """You are a strictly constrained Flutter UI Prototyper. Write ONLY the GeneratedAppBody widget code based the blueprint. Wrap in ```dart fences. 
    CRITICAL RULES:
    1. ZERO CUSTOM CLASSES: Do NOT create any custom classes, data models, or sub-widgets.
    2. PURE UI ONLY: Use ONLY standard Flutter widgets.
    3. HARDCODE EVERYTHING: No external packages, no HTTP, no state management.

    EXAMPLE OF PERFECT OUTPUT:
    ```dart
    class GeneratedAppBody extends StatelessWidget {
      @override
      Widget build(BuildContext context) {
        return Scaffold(
          appBar: AppBar(title: Text('Cricket Updates')),
          body: ListView(
            padding: EdgeInsets.all(16.0),
            children: [ Card(child: ListTile(title: Text('India vs Australia')))],
          ),
        );
      }
    }
    ```
    You MUST follow the exact structural pattern of the example above."""

    max_attempts = 3
    draft_code = ""
    logs = ""

    # 3. THE CRITIC LOOP (Self-Healing Circuit)
    for attempt in range(max_attempts):
        # Temperature Annealing: 0.7 (Creative) -> 0.3 (Focused) -> 0.0 (Robotic logic)
        current_temp = [0.7, 0.3, 0.0][attempt]
        attempt_label = f"Attempt {attempt + 1}/{max_attempts}"

        yield f"⚙️ [{attempt_label}] Maker writing code (Temp: {current_temp})...", blueprint, placeholder

        # Dynamic Prompting based on attempt
        if attempt == 0:
            user_prompt = f"Blueprint:\n{blueprint}"
        else:
            # Failsafe: Truncate logs to protect API token limits
            truncated_logs = logs[-1500:] if len(logs) > 1500 else logs
            user_prompt = f"CRITICAL CRITIC FEEDBACK:\nYour last code failed to compile. Fix the exact errors below.\n\nCOMPILER LOGS:\n{truncated_logs}\n\nORIGINAL BLUEPRINT:\n{blueprint}\n\nPREVIOUS BROKEN CODE:\n{draft_code}"

        draft_code_raw = _llm(maker_sys, user_prompt, temp=current_temp)
        draft_code = draft_code_raw.replace("```dart", "").replace("```", "").strip()

        yield f"🧵 [{attempt_label}] Stitching imports...", blueprint, placeholder
        
        draft_lines = draft_code.split('\n')
        ai_imports = [line for line in draft_lines if line.strip().startswith('import ')]
        ai_body = [line for line in draft_lines if not line.strip().startswith('import ')]
                
        clean_draft_code = '\n'.join(ai_body)
        all_imports = f"{BASE_IMPORTS}\n" + '\n'.join(ai_imports)
        final_code = f"{all_imports}\n{BASE_MAIN}\n{clean_draft_code}"

        yield f"🏗️ [{attempt_label}] Compiling Engine (Wait 15-30s)...", blueprint, placeholder
        success, logs = compile_to_web(final_code)

        if success:
            saved_id = save_to_memory(app_idea, final_code)
            iframe_html = '<iframe src="/preview/index.html" width="100%" height="600px" style="border:1px solid #1e2535; border-radius: 8px; background-color: #ffffff;"></iframe>'
            yield f"🚀 App Compiled! Project #{saved_id} is live.", blueprint, iframe_html
            return # Exit the loop and function completely

    # 4. GRACEFUL DEGRADATION (Circuit Breaker Tripped)
    # If the code reaches here, all 3 attempts failed. Output the raw code so the human can step in.
    error_html = f"""
    <div style='background:#1e2535; color:#ff4d4f; padding:15px; height:600px; overflow:auto; border-radius:8px; font-family:monospace;'>
        <h3 style='margin-top:0;'>🛑 Circuit Breaker Tripped</h3>
        <p>The AI failed to heal the code after 3 attempts. Manual override required.</p>
        <hr style='border-color: #ff4d4f;'/>
        <h4 style='color:#4ade80;'>1. Last Compiler Error:</h4>
        <pre style='white-space: pre-wrap; font-size:12px;'>{logs[-1500:]}</pre>
        <hr style='border-color: #ff4d4f;'/>
        <h4 style='color:#4ade80;'>2. Broken Dart Code (For Manual Fix):</h4>
        <pre style='color:#e5e7eb; white-space: pre-wrap; font-size:12px;'>{final_code}</pre>
    </div>
    """
    yield "🛑 Pipeline Halted. Manual override required.", blueprint, error_html


# ─────────────────────────────────────────────────────────────────
# GRADIO UI & FASTAPI MOUNTING
# ─────────────────────────────────────────────────────────────────
def build_ui():
    with gr.Blocks() as demo:
        gr.Markdown("# 🛠️ CodeCraft: Live Compiler Engine\nMulti-Agent logic with sandboxed Flutter compilation.")
        
        with gr.Row():
            prompt_input = gr.Textbox(label="App Idea", lines=2)
            deploy_btn = gr.Button("Deploy & Compile", variant="primary")
            
        status_tracker = gr.Textbox(label="Live Pipeline Status", interactive=False)
        
        with gr.Row():
            blueprint_output = gr.Textbox(label="Architect Blueprint", interactive=False)
            placeholder = "<div style='height:600px; border:2px dashed #4ade80; display:flex; align-items:center; justify-content:center; border-radius:8px; color:#4ade80; font-family:monospace; background:#0d1117;'>[ Live App Preview Will Render Here ]</div>"
            app_preview = gr.HTML(label="Live Application", value=placeholder)

        deploy_btn.click(fn=autonomous_agentic_loop, inputs=prompt_input, outputs=[status_tracker, blueprint_output, app_preview])
    return demo

init_db()
demo = build_ui()

app = FastAPI()
os.makedirs(f"{FLUTTER_PROJECT_DIR}/build/web", exist_ok=True)
app.mount("/preview", StaticFiles(directory=f"{FLUTTER_PROJECT_DIR}/build/web", html=True), name="preview")
app = gr.mount_gradio_app(app, demo, path="/")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=7860)