use std::net::TcpStream;
use std::path::PathBuf;
use std::process::{Child, Command};
use std::sync::Mutex;
use std::time::Duration;
use serde::{Deserialize, Serialize};

#[derive(Serialize, Deserialize, Clone, Debug)]
pub struct BackendStatus {
    pub is_online: bool,
    pub is_managed: bool,
    pub message: String,
}

pub struct BackendManager {
    child: Mutex<Option<Child>>,
    auth_token: String,
}

impl BackendManager {
    pub fn new() -> Self {
        Self {
            child: Mutex::new(None),
            auth_token: uuid::Uuid::new_v4().to_string(),
        }
    }

    pub fn get_token(&self) -> String {
        self.auth_token.clone()
    }

    pub fn is_port_open() -> bool {
        TcpStream::connect_timeout(
            &"127.0.0.1:8000".parse().unwrap(),
            Duration::from_millis(300),
        )
        .is_ok()
    }

    fn find_backend_root() -> Option<PathBuf> {
        let candidates = [
            PathBuf::from("../../backend"),
            PathBuf::from("../backend"),
            PathBuf::from("./backend"),
            PathBuf::from("backend"),
        ];

        for candidate in &candidates {
            let py_path = candidate.join(".venv/bin/python");
            let app_path = candidate.join("app/main.py");
            if py_path.exists() && app_path.exists() {
                if let Ok(canon) = candidate.canonicalize() {
                    return Some(canon);
                }
            }
        }
        None
    }

    pub fn spawn_if_needed(&self) -> Result<BackendStatus, String> {
        if Self::is_port_open() {
            return Ok(BackendStatus {
                is_online: true,
                is_managed: false,
                message: "Backend is already running on port 8000.".into(),
            });
        }

        let backend_root = Self::find_backend_root().ok_or_else(|| {
            "Could not locate backend directory with virtual environment.".to_string()
        })?;

        let python_bin = backend_root.join(".venv/bin/python");

        let mut cmd = Command::new(&python_bin);
        cmd.args(["-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", "8000"])
            .env("GIPSY_AUTH_TOKEN", &self.auth_token)
            .current_dir(&backend_root);

        let child = cmd
            .spawn()
            .map_err(|e| format!("Failed to spawn Python backend: {}", e))?;

        if let Ok(mut lock) = self.child.lock() {
            *lock = Some(child);
        }

        for _ in 0..15 {
            std::thread::sleep(Duration::from_millis(200));
            if Self::is_port_open() {
                return Ok(BackendStatus {
                    is_online: true,
                    is_managed: true,
                    message: "Spawned and connected to Python backend.".into(),
                });
            }
        }

        Ok(BackendStatus {
            is_online: false,
            is_managed: true,
            message: "Spawned Python process, waiting for port 8000 to open.".into(),
        })
    }

    pub fn stop(&self) {
        if let Ok(mut lock) = self.child.lock() {
            if let Some(mut child) = lock.take() {
                let _ = child.kill();
                let _ = child.wait();
            }
        }
    }

    pub fn get_status(&self) -> BackendStatus {
        let is_online = Self::is_port_open();
        let is_managed = self.child.lock().map(|g| g.is_some()).unwrap_or(false);

        BackendStatus {
            is_online,
            is_managed,
            message: if is_online {
                "Backend online and reachable.".into()
            } else {
                "Backend offline.".into()
            },
        }
    }
}
