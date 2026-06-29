use std::io::{BufRead, BufReader, Write};
use std::path::PathBuf;
use std::process::{Child, ChildStdin, Command, Stdio};
use std::sync::Mutex;

use tauri::{Emitter, Manager, RunEvent, State};

/// Holds the sidecar's stdin (for `ipc_send`) and the child handle (to kill it
/// on app exit, so the Python backend never orphans).
struct Sidecar {
    stdin: Mutex<ChildStdin>,
    child: Mutex<Option<Child>>,
}

/// Write one NDJSON request line to the sidecar's stdin.
#[tauri::command]
fn ipc_send(line: String, sidecar: State<'_, Sidecar>) -> Result<(), String> {
    let mut stdin = sidecar.stdin.lock().map_err(|e| e.to_string())?;
    stdin.write_all(line.as_bytes()).map_err(|e| e.to_string())?;
    stdin.write_all(b"\n").map_err(|e| e.to_string())?;
    stdin.flush().map_err(|e| e.to_string())?;
    Ok(())
}

/// Repo root, computed from the crate dir: desktop/src-tauri -> ../.. -> repo.
fn repo_root() -> PathBuf {
    PathBuf::from(env!("CARGO_MANIFEST_DIR")).join("../..")
}

/// How the sidecar is launched. In a packaged app the frozen binary sits next to
/// the app executable; in dev there is no such sibling, so we run it via uv.
enum SidecarKind {
    Bundled(PathBuf),
    Dev,
}

/// Bundled if a `productagents-ipc[.exe]` exists next to the current executable
/// (Tauri's externalBin lands there), else Dev.
fn sidecar_kind() -> SidecarKind {
    let name = if cfg!(windows) {
        "productagents-ipc.exe"
    } else {
        "productagents-ipc"
    };
    if let Ok(exe) = std::env::current_exe() {
        if let Some(dir) = exe.parent() {
            let candidate = dir.join(name);
            if candidate.exists() {
                return SidecarKind::Bundled(candidate);
            }
        }
    }
    SidecarKind::Dev
}

/// Build the (unspawned) command for the resolved sidecar.
fn sidecar_command() -> Command {
    match sidecar_kind() {
        SidecarKind::Bundled(path) => Command::new(path),
        SidecarKind::Dev => {
            let mut cmd = Command::new("uv");
            cmd.args(["run", "productagents", "ipc"])
                .current_dir(repo_root());
            cmd
        }
    }
}

pub fn run() {
    let app = tauri::Builder::default()
        .setup(|app| {
            let mut child = sidecar_command()
                .stdin(Stdio::piped())
                .stdout(Stdio::piped())
                .spawn()
                .expect("failed to spawn the IPC sidecar");

            let stdout = child.stdout.take().expect("sidecar stdout missing");
            let stdin = child.stdin.take().expect("sidecar stdin missing");
            app.manage(Sidecar {
                stdin: Mutex::new(stdin),
                child: Mutex::new(Some(child)),
            });

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
        .build(tauri::generate_context!())
        .expect("error while building tauri application");

    app.run(|app, event| {
        if let RunEvent::ExitRequested { .. } = event {
            if let Some(sidecar) = app.try_state::<Sidecar>() {
                if let Ok(mut guard) = sidecar.child.lock() {
                    if let Some(mut child) = guard.take() {
                        let _ = child.kill();
                    }
                }
            }
        }
    });
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn falls_back_to_dev_without_a_bundled_binary() {
        // The test runner has no `productagents-ipc` sibling of the test exe,
        // so resolution must choose the dev (uv) path.
        assert!(matches!(sidecar_kind(), SidecarKind::Dev));
    }
}
