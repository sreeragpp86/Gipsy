use std::net::TcpStream;
use std::path::PathBuf;
use std::process::{Child, Command};
use std::sync::Mutex;
use std::time::Duration;

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

    fn is_valid_backend_dir(path: &PathBuf) -> Option<PathBuf> {
        if path.join(".venv/bin/python").is_file() && path.join("app/main.py").is_file() {
            return path.canonicalize().ok();
        }
        None
    }

    fn find_backend_root() -> Option<PathBuf> {
        if let Ok(custom_dir) = std::env::var("GIPSY_BACKEND_DIR") {
            if let Some(canon) = Self::is_valid_backend_dir(&PathBuf::from(custom_dir)) {
                return Some(canon);
            }
        }

        if let Ok(exe_path) = std::env::current_exe() {
            let mut cur = exe_path.parent();
            for _ in 0..6 {
                let Some(parent) = cur else { break };
                for rel in ["backend", "Resources/backend"] {
                    if let Some(canon) = Self::is_valid_backend_dir(&parent.join(rel)) {
                        return Some(canon);
                    }
                }
                cur = parent.parent();
            }
        }

        for rel in ["../../backend", "../backend", "./backend", "backend"] {
            if let Some(canon) = Self::is_valid_backend_dir(&PathBuf::from(rel)) {
                return Some(canon);
            }
        }

        None
    }

    pub fn spawn_if_needed(&self) -> Result<(), String> {
        if Self::is_port_open() {
            return Ok(());
        }

        let backend_root = Self::find_backend_root().ok_or_else(|| {
            "Could not locate backend directory with virtual environment.".to_string()
        })?;

        let python_bin = backend_root.join(".venv/bin/python");

        let mut cmd = Command::new(&python_bin);
        cmd.args([
            "-m",
            "uvicorn",
            "app.main:app",
            "--host",
            "127.0.0.1",
            "--port",
            "8000",
        ])
        .env("GIPSY_AUTH_TOKEN", &self.auth_token)
        .env_remove("PYTHONPATH")
        .env_remove("PYTHONHOME")
        .env_remove("DYLD_LIBRARY_PATH")
        .env_remove("DYLD_INSERT_LIBRARIES")
        .env_remove("LD_PRELOAD")
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
                return Ok(());
            }
        }

        Ok(())
    }

    pub fn stop(&self) {
        if let Ok(mut lock) = self.child.lock() {
            if let Some(mut child) = lock.take() {
                let _ = child.kill();
                let _ = child.wait();
            }
        }
    }
}
