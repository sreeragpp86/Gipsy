mod backend;

use backend::BackendManager;
use std::sync::Arc;
use tauri::menu::{Menu, MenuItem};
use tauri::tray::{MouseButton, MouseButtonState, TrayIconBuilder, TrayIconEvent};
use tauri::{ActivationPolicy, AppHandle, LogicalSize, Manager, State, WindowEvent};
use tauri_plugin_autostart::MacosLauncher;
use tauri_plugin_global_shortcut::{Code, GlobalShortcutExt, Modifiers, Shortcut, ShortcutState};

#[cfg(target_os = "macos")]
use window_vibrancy::{NSVisualEffectMaterial, NSVisualEffectState, apply_vibrancy};

fn toggle_window_visibility(app: &AppHandle) {
    if let Some(window) = app.get_webview_window("main") {
        if window.is_visible().unwrap_or(false) {
            let _ = window.hide();
        } else {
            let _ = window.show();
            let _ = window.set_focus();
        }
    }
}

#[tauri::command]
fn drag_window(app: AppHandle) -> Result<(), String> {
    if let Some(window) = app.get_webview_window("main") {
        window.start_dragging().map_err(|e| e.to_string())
    } else {
        Err("Main window not found".into())
    }
}

#[tauri::command]
fn set_hud_mode(app: AppHandle, mode: String) -> Result<(), String> {
    if let Some(window) = app.get_webview_window("main") {
        match mode.as_str() {
            "pill" => {
                let _ = window.set_min_size(Some(LogicalSize::new(200.0, 48.0)));
                window
                    .set_size(LogicalSize::new(280.0, 56.0))
                    .map_err(|e| e.to_string())?;
                let _ = window.set_resizable(false);
            }
            "expanded" => {
                let _ = window.set_min_size(Some(LogicalSize::new(520.0, 500.0)));
                window
                    .set_size(LogicalSize::new(780.0, 660.0))
                    .map_err(|e| e.to_string())?;
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
fn get_auth_token(manager: State<'_, Arc<BackendManager>>) -> String {
    manager.get_token()
}

#[tauri::command]
fn set_window_visible(app: AppHandle, visible: bool) -> Result<(), String> {
    if let Some(window) = app.get_webview_window("main") {
        if visible {
            window.show().map_err(|e| e.to_string())?;
        } else {
            window.hide().map_err(|e| e.to_string())?;
        }
        Ok(())
    } else {
        Err("Main window not found".into())
    }
}

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    let backend_manager = Arc::new(BackendManager::new());
    let backend_setup = backend_manager.clone();
    let backend_exit = backend_manager.clone();

    tauri::Builder::default()
        .manage(backend_manager)
        .on_window_event(|window, event| {
            if let WindowEvent::CloseRequested { api, .. } = event {
                api.prevent_close();
                let _ = window.hide();
            }
        })
        .setup(move |app| {
            #[cfg(target_os = "macos")]
            app.set_activation_policy(ActivationPolicy::Accessory);

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
                        Some(16.0),
                    );
                }
            }

            let shortcut = Shortcut::new(Some(Modifiers::ALT), Code::Space);
            let shortcut_match = shortcut.clone();
            app.handle().plugin(
                tauri_plugin_global_shortcut::Builder::new()
                    .with_handler(move |app, s, event| {
                        if s == &shortcut_match && event.state() == ShortcutState::Pressed {
                            toggle_window_visibility(app);
                        }
                    })
                    .build(),
            )?;
            let _ = app.global_shortcut().register(shortcut);

            app.handle().plugin(tauri_plugin_autostart::init(
                MacosLauncher::LaunchAgent,
                Some(vec!["--autostart"]),
            ))?;

            let toggle_i = MenuItem::with_id(app, "toggle", "Toggle Gipsy", true, None::<&str>)?;
            let quit_i = MenuItem::with_id(app, "quit", "Quit", true, None::<&str>)?;
            let tray_menu = Menu::with_items(app, &[&toggle_i, &quit_i])?;

            let tray_icon = tauri::include_image!("icons/tray-icon@2x.png");

            let _tray = TrayIconBuilder::new()
                .icon(tray_icon)
                .icon_as_template(true)
                .tooltip("Project Gipsy")
                .menu(&tray_menu)
                .show_menu_on_left_click(false)
                .on_menu_event(|app, event| match event.id.as_ref() {
                    "toggle" => toggle_window_visibility(app),
                    "quit" => app.exit(0),
                    _ => {}
                })
                .on_tray_icon_event(|tray, event| {
                    if let TrayIconEvent::Click {
                        button: MouseButton::Left,
                        button_state: MouseButtonState::Up,
                        ..
                    } = event
                    {
                        toggle_window_visibility(tray.app_handle());
                    }
                })
                .build(app)?;

            let _ = backend_setup.spawn_if_needed();

            Ok(())
        })
        .invoke_handler(tauri::generate_handler![
            drag_window,
            set_hud_mode,
            get_auth_token,
            set_window_visible
        ])
        .build(tauri::generate_context!())
        .expect("error while building tauri application")
        .run(move |_app_handle, event| {
            if let tauri::RunEvent::Exit = event {
                backend_exit.stop();
            }
        });
}
