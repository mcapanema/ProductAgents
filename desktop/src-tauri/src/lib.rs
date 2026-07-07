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
    stdin
        .write_all(line.as_bytes())
        .map_err(|e| e.to_string())?;
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
    // Debug builds ALWAYS run the dev sidecar. `externalBin` forces a sidecar
    // file to exist for every local build and `tauri dev` copies it next to
    // the executable — so a placeholder (or a stale frozen binary from an old
    // `make build-sidecar`) would otherwise silently hijack dev runs: the
    // placeholder exits immediately and every ipc_send gets a broken pipe.
    if cfg!(debug_assertions) {
        return SidecarKind::Dev;
    }
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

/// Spawn the sidecar and wire its stdout to `ipc://message` events.
/// Returns the child handle and its stdin for `ipc_send`.
fn spawn_sidecar(handle: &tauri::AppHandle) -> Result<(Child, ChildStdin), String> {
    let mut child = sidecar_command()
        .stdin(Stdio::piped())
        .stdout(Stdio::piped())
        .stderr(Stdio::piped())
        .spawn()
        .map_err(|e| format!("failed to spawn the IPC sidecar: {e}"))?;
    let stdout = child.stdout.take().ok_or("sidecar stdout missing")?;
    let stderr = child.stderr.take().ok_or("sidecar stderr missing")?;
    let stdin = child.stdin.take().ok_or("sidecar stdin missing")?;

    // Drain stderr so a packaged-app traceback reaches the terminal/log instead
    // of vanishing (a lost traceback already cost one debugging cycle — the
    // PyInstaller entry-point incident).
    std::thread::spawn(move || {
        let reader = BufReader::new(stderr);
        for line in reader.lines() {
            match line {
                Ok(text) => eprintln!("[sidecar] {text}"),
                Err(_) => break,
            }
        }
    });

    let handle = handle.clone();
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
        // stdout closed → the sidecar is gone. Tell the webview so the client
        // rejects every in-flight request instead of showing "running" forever.
        let _ = handle.emit("ipc://closed", ());
    });
    Ok((child, stdin))
}

pub fn run() {
    let app = tauri::Builder::default()
        .plugin(tauri_plugin_updater::Builder::new().build())
        .plugin(tauri_plugin_process::init())
        .setup(|app| {
            let (child, stdin) =
                spawn_sidecar(&app.handle().clone()).expect("failed to spawn the IPC sidecar");
            app.manage(Sidecar {
                stdin: Mutex::new(stdin),
                child: Mutex::new(Some(child)),
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
                        let _ = child.wait(); // reap so the child never zombies
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
    fn debug_builds_ignore_a_bundled_binary() {
        // `externalBin` forces a (placeholder) sidecar binary to exist for
        // local builds, and `tauri dev` copies it next to the executable. A
        // debug build must never spawn it — a leftover `#!/bin/sh exit 0`
        // placeholder dies instantly and every ipc_send gets a broken pipe.
        let exe = std::env::current_exe().unwrap();
        let sibling = exe.parent().unwrap().join("productagents-ipc");
        std::fs::write(&sibling, b"#!/bin/sh\nexit 0\n").unwrap();
        let kind = sidecar_kind();
        let _ = std::fs::remove_file(&sibling);
        assert!(matches!(kind, SidecarKind::Dev));
    }

    #[test]
    fn falls_back_to_dev_without_a_bundled_binary() {
        // The test runner has no `productagents-ipc` sibling of the test exe,
        // so resolution must choose the dev (uv) path.
        assert!(matches!(sidecar_kind(), SidecarKind::Dev));
    }
}
