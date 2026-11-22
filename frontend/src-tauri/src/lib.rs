use tauri::{AppHandle, LogicalSize, Manager};

#[cfg(target_os = "macos")]
use window_vibrancy::{apply_vibrancy, NSVisualEffectMaterial, NSVisualEffectState};

#[tauri::command]
fn set_hud_mode(app: AppHandle, mode: String) -> Result<(), String> {
    if let Some(window) = app.get_webview_window("main") {
        match mode.as_str() {
            "pill" => {
                window.set_size(LogicalSize::new(280.0, 56.0)).map_err(|e| e.to_string())?;
                let _ = window.set_resizable(false);
            }
            "expanded" => {
                window.set_size(LogicalSize::new(780.0, 520.0)).map_err(|e| e.to_string())?;
                let _ = window.set_resizable(true);
            }
            _ => return Err(format!("Unknown HUD mode: {}", mode)),
        }
        Ok(())
    } else {
        Err("Main window not found".into())
    }
}

#[tauri::command]
fn set_click_through(app: AppHandle, ignore: bool) -> Result<(), String> {
    if let Some(window) = app.get_webview_window("main") {
        window.set_ignore_cursor_events(ignore).map_err(|e| e.to_string())
    } else {
        Err("Main window not found".into())
    }
}

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    tauri::Builder::default()
        .setup(|app| {
            if cfg!(debug_assertions) {
                app.handle().plugin(
                    tauri_plugin_log::Builder::default()
                        .level(log::LevelFilter::Info)
                        .build(),
                )?;
            }

            if let Some(window) = app.get_webview_window("main") {
                #[cfg(target_os = "macos")]
                {
                    let _ = apply_vibrancy(
                        &window,
                        NSVisualEffectMaterial::HudWindow,
                        Some(NSVisualEffectState::Active),
                        Some(18.0),
                    );
                }
            }

            Ok(())
        })
        .invoke_handler(tauri::generate_handler![set_hud_mode, set_click_through])
        .run(tauri::generate_context!())
        .expect("error while building tauri application");
}
