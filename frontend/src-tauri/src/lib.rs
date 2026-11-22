mod backend;

use std::sync::Arc;
use tauri::menu::{Menu, MenuItem};
use tauri::tray::TrayIconBuilder;
use tauri::{AppHandle, LogicalSize, Manager, State};
use tauri_plugin_autostart::MacosLauncher;
use tauri_plugin_global_shortcut::{Code, GlobalShortcutExt, Modifiers, Shortcut, ShortcutState};
use backend::{BackendManager, BackendStatus};

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
                window.set_size(LogicalSize::new(780.0, 660.0)).map_err(|e| e.to_string())?;
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

#[tauri::command]
fn get_backend_status(manager: State<'_, Arc<BackendManager>>) -> BackendStatus {
    manager.get_status()
}

#[tauri::command]
fn start_backend(manager: State<'_, Arc<BackendManager>>) -> Result<BackendStatus, String> {
    manager.spawn_if_needed()
}

#[tauri::command]
fn stop_backend(manager: State<'_, Arc<BackendManager>>) -> Result<(), String> {
    manager.stop();
    Ok(())
}

#[tauri::command]
fn get_auth_token(manager: State<'_, Arc<BackendManager>>) -> String {
    manager.get_token()
}

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    let backend_manager = Arc::new(BackendManager::new());
    let backend_setup = backend_manager.clone();
    let backend_exit = backend_manager.clone();

    tauri::Builder::default()
        .manage(backend_manager)
        .setup(move |app| {
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

            let shortcut = Shortcut::new(Some(Modifiers::ALT), Code::Space);
            let shortcut_match = shortcut.clone();
            app.handle().plugin(
                tauri_plugin_global_shortcut::Builder::new()
                    .with_handler(move |app, s, event| {
                        if s == &shortcut_match && event.state() == ShortcutState::Pressed {
                            if let Some(window) = app.get_webview_window("main") {
                                let is_visible = window.is_visible().unwrap_or(false);
                                if is_visible {
                                    let _ = window.hide();
                                } else {
                                    let _ = window.show();
                                    let _ = window.set_focus();
                                }
                            }
                        }
                    })
                    .build(),
            )?;
            let _ = app.global_shortcut().register(shortcut);

            app.handle().plugin(
                tauri_plugin_autostart::init(
                    MacosLauncher::LaunchAgent,
                    Some(vec!["--autostart"]),
                )
            )?;

            let status_i = MenuItem::with_id(app, "status", "Gipsy • Standby", false, None::<&str>)?;
            let toggle_i = MenuItem::with_id(app, "toggle", "Toggle HUD (⌥ + Space)", true, None::<&str>)?;
            let quit_i = MenuItem::with_id(app, "quit", "Quit Gipsy", true, None::<&str>)?;

            let tray_menu = Menu::with_items(app, &[&status_i, &toggle_i, &quit_i])?;

            let mut tray_builder = TrayIconBuilder::new()
                .menu(&tray_menu)
                .show_menu_on_left_click(true)
                .on_menu_event(|app, event| {
                    match event.id.as_ref() {
                        "quit" => {
                            app.exit(0);
                        }
                        "toggle" => {
                            if let Some(window) = app.get_webview_window("main") {
                                let is_visible = window.is_visible().unwrap_or(false);
                                if is_visible {
                                    let _ = window.hide();
                                } else {
                                    let _ = window.show();
                                    let _ = window.set_focus();
                                }
                            }
                        }
                        _ => {}
                    }
                });

            if let Some(icon) = app.default_window_icon() {
                tray_builder = tray_builder.icon(icon.clone());
            }

            let _ = tray_builder.build(app)?;

            let _ = backend_setup.spawn_if_needed();

            Ok(())
        })
        .invoke_handler(tauri::generate_handler![
            set_hud_mode,
            set_click_through,
            get_backend_status,
            start_backend,
            stop_backend,
            get_auth_token
        ])
        .build(tauri::generate_context!())
        .expect("error while building tauri application")
        .run(move |_app_handle, event| {
            if let tauri::RunEvent::Exit = event {
                backend_exit.stop();
            }
        });
}
