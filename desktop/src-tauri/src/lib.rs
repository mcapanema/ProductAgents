use std::io::{BufRead, BufReader, Write};
use std::path::PathBuf;
use std::process::{ChildStdin, Command, Stdio};
use std::sync::Mutex;

use tauri::{Emitter, Manager, State};

/// Holds the sidecar's stdin so `ipc_send` can write request lines to it.
struct Sidecar(Mutex<ChildStdin>);

/// Write one NDJSON request line to the sidecar's stdin.
#[tauri::command]
fn ipc_send(line: String, sidecar: State<'_, Sidecar>) -> Result<(), String> {
    let mut stdin = sidecar.0.lock().map_err(|e| e.to_string())?;
    stdin.write_all(line.as_bytes()).map_err(|e| e.to_string())?;
    stdin.write_all(b"\n").map_err(|e| e.to_string())?;
    stdin.flush().map_err(|e| e.to_string())?;
    Ok(())
}

/// Repo root, computed from the crate dir: desktop/src-tauri -> ../.. -> repo.
fn repo_root() -> PathBuf {
    PathBuf::from(env!("CARGO_MANIFEST_DIR")).join("../..")
}

pub fn run() {
    tauri::Builder::default()
        .setup(|app| {
            // ponytail: dev spawn via `uv run productagents ipc`. Phase 8e replaces
            // this with a bundled PyInstaller sidecar binary (Tauri externalBin).
            let mut child = Command::new("uv")
                .args(["run", "productagents", "ipc"])
                .current_dir(repo_root())
                .stdin(Stdio::piped())
                .stdout(Stdio::piped())
                .spawn()
                .expect("failed to spawn `uv run productagents ipc`");

            let stdout = child.stdout.take().expect("sidecar stdout missing");
            let stdin = child.stdin.take().expect("sidecar stdin missing");
            app.manage(Sidecar(Mutex::new(stdin)));

            let handle = app.handle().clone();
            std::thread::spawn(move || {
                let reader = BufReader::new(stdout);
                for line in reader.lines() {
                    match line {
                        Ok(text) => {
                            let _ = handle.emit("ipc://message", text);
                        }
                        Err(_) => break,
                    }
                }
            });
            Ok(())
        })
        .invoke_handler(tauri::generate_handler![ipc_send])
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}
