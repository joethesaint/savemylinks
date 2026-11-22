//! The icon by the clock (the Windows notification area, the macOS menu bar). It says SaveMyLinks
//! is on, opens your library with a click, and switches it off from its menu, so there is no
//! terminal window to keep open. Linux keeps the terminal for now (a tray there needs GTK).
//!
//! Desktop Clippy (#36): "Clippy on the desktop" in the menu puts him in a small see-through window
//! that stays on top of other windows (static/desk.html in a web view). Double-click him to save a
//! link. The window is only as big as Clippy, so it doesn't block clicks on the desktop, and grows
//! while his save box or a message shows. The choice is remembered next to the library file.
use std::path::PathBuf;
use std::time::{Duration, Instant};

use tao::dpi::{LogicalSize, PhysicalPosition};
use tao::event::{Event, StartCause, WindowEvent};
use tao::event_loop::{ControlFlow, EventLoopBuilder, EventLoopWindowTarget};
use tao::window::{Window, WindowBuilder};
use tray_icon::menu::{CheckMenuItem, Menu, MenuEvent, MenuItem, PredefinedMenuItem};
use tray_icon::{Icon, MouseButton, MouseButtonState, TrayIconBuilder, TrayIconEvent};
use wry::{WebView, WebViewBuilder};

const ICON_PNG: &[u8] = include_bytes!("../../app/static/art/icon-32.png");
const SMALL: (f64, f64) = (180.0, 150.0); // just Clippy
const LARGE: (f64, f64) = (380.0, 330.0); // Clippy with his save box or a message

/// What desk.html asks for, through window.ipc.postMessage.
#[derive(Debug, Clone, Copy)]
enum Desk {
    Drag,
    Grow,
    Shrink,
    Hide,
}

fn icon() -> Option<Icon> {
    let mut reader = png::Decoder::new(ICON_PNG).read_info().ok()?;
    let mut buf = vec![0; reader.output_buffer_size()];
    let info = reader.next_frame(&mut buf).ok()?;
    if info.color_type != png::ColorType::Rgba || info.bit_depth != png::BitDepth::Eight {
        return None;
    }
    buf.truncate(info.buffer_size());
    Icon::from_rgba(buf, info.width, info.height).ok()
}

/// Show the folder that holds the library file in Explorer or Finder.
fn show_folder(db_path: &str) {
    let dir = std::path::Path::new(db_path).parent().map(|p| p.to_path_buf()).unwrap_or_default();
    #[cfg(windows)]
    let _ = std::process::Command::new("explorer").arg(&dir).spawn();
    #[cfg(target_os = "macos")]
    let _ = std::process::Command::new("open").arg(&dir).spawn();
}

/// Keep the bottom-right corner where it is while the window changes size (Clippy sits there).
fn resize_anchored(w: &Window, size: (f64, f64)) {
    let before = w.outer_size();
    let pos = w.outer_position().unwrap_or_default();
    w.set_inner_size(LogicalSize::new(size.0, size.1));
    let after = w.outer_size();
    w.set_outer_position(PhysicalPosition::new(
        pos.x + before.width as i32 - after.width as i32,
        pos.y + before.height as i32 - after.height as i32,
    ));
}

/// A borderless, see-through, always-on-top window with desk.html in it, bottom right of the screen.
fn open_desk(target: &EventLoopWindowTarget<Desk>, addr: &str, proxy: tao::event_loop::EventLoopProxy<Desk>) -> Option<(Window, WebView)> {
    #[allow(unused_mut)]
    let mut b = WindowBuilder::new()
        .with_title("Clippy")
        .with_decorations(false)
        .with_transparent(true)
        .with_always_on_top(true)
        .with_resizable(false)
        .with_inner_size(LogicalSize::new(SMALL.0, SMALL.1));
    #[cfg(windows)]
    {
        use tao::platform::windows::WindowBuilderExtWindows;
        b = b.with_skip_taskbar(true).with_undecorated_shadow(false);
    }
    let window = b.build(target).ok()?;
    if let Some(m) = target.primary_monitor() {
        let (ms, mp, ws) = (m.size(), m.position(), window.outer_size());
        let margin = (48.0 * m.scale_factor()) as i32;
        window.set_outer_position(PhysicalPosition::new(
            mp.x + ms.width as i32 - ws.width as i32 - margin,
            mp.y + ms.height as i32 - ws.height as i32 - margin * 2, // above the taskbar
        ));
    }
    let webview = WebViewBuilder::new()
        .with_url(format!("{addr}static/desk.html"))
        .with_transparent(true)
        .with_ipc_handler(move |req: wry::http::Request<String>| {
            let ev = match req.body().as_str() {
                "drag" => Desk::Drag,
                "open" => Desk::Grow,
                "close" => Desk::Shrink,
                "hide" => Desk::Hide,
                _ => return,
            };
            let _ = proxy.send_event(ev);
        })
        .build(&window)
        .ok()?;
    Some((window, webview))
}

/// Runs on the main thread until "Switch off" is chosen; `stop` shuts the server down first.
pub fn run(addr: String, db_path: String, stop: impl FnOnce() + 'static) -> ! {
    #[allow(unused_mut)]
    let mut event_loop = EventLoopBuilder::<Desk>::with_user_event().build();
    #[cfg(target_os = "macos")]
    {
        // A menu-bar app: no Dock icon.
        use tao::platform::macos::{ActivationPolicy, EventLoopExtMacOS};
        event_loop.set_activation_policy(ActivationPolicy::Accessory);
    }
    let proxy = event_loop.create_proxy();

    // Desktop Clippy on or off, remembered next to the library file.
    let desk_flag: PathBuf = std::path::Path::new(&db_path).with_file_name("desktop-clippy.on");
    let desk_wanted = desk_flag.exists();

    let menu = Menu::new();
    let status = MenuItem::new("SaveMyLinks is on", false, None);
    let open = MenuItem::new("Open your library", true, None);
    let clippy = CheckMenuItem::new("Clippy on the desktop", true, desk_wanted, None);
    let folder = MenuItem::new("Show where your links are kept", true, None);
    let quit = MenuItem::new("Switch off SaveMyLinks", true, None);
    let _ = menu.append_items(&[
        &status,
        &PredefinedMenuItem::separator(),
        &open,
        &clippy,
        &folder,
        &PredefinedMenuItem::separator(),
        &quit,
    ]);
    let (open_id, clippy_id, folder_id, quit_id) = (open.id().clone(), clippy.id().clone(), folder.id().clone(), quit.id().clone());
    let tooltip = format!("SaveMyLinks is on ({})\nClick to open your library", addr.trim_end_matches('/'));

    let mut tray = None;
    let mut desk: Option<(Window, WebView)> = None;
    let mut stop = Some(stop);
    let set_flag = move |on: bool| {
        let _ = if on { std::fs::write(&desk_flag, b"on") } else { std::fs::remove_file(&desk_flag) };
    };
    event_loop.run(move |event, target, control_flow| {
        *control_flow = ControlFlow::WaitUntil(Instant::now() + Duration::from_millis(200));

        match event {
            // macOS needs the loop running before the icon is made.
            Event::NewEvents(StartCause::Init) => {
                let mut b = TrayIconBuilder::new().with_menu(Box::new(menu.clone())).with_tooltip(&tooltip);
                if let Some(i) = icon() {
                    b = b.with_icon(i);
                }
                tray = b.build().ok();
                if desk_wanted {
                    desk = open_desk(target, &addr, proxy.clone());
                }
            }
            Event::UserEvent(ev) => {
                if let Some((w, _)) = &desk {
                    match ev {
                        Desk::Drag => { let _ = w.drag_window(); }
                        Desk::Grow => resize_anchored(w, LARGE),
                        Desk::Shrink => resize_anchored(w, SMALL),
                        Desk::Hide => {
                            desk = None;
                            clippy.set_checked(false);
                            set_flag(false);
                        }
                    }
                }
            }
            Event::WindowEvent { event: WindowEvent::CloseRequested, .. } => {
                desk = None;
                clippy.set_checked(false);
                set_flag(false);
            }
            _ => {}
        }

        while let Ok(ev) = MenuEvent::receiver().try_recv() {
            if ev.id == open_id {
                let _ = webbrowser::open(&addr);
            } else if ev.id == clippy_id {
                let on = clippy.is_checked();
                if on && desk.is_none() {
                    desk = open_desk(target, &addr, proxy.clone());
                    if desk.is_none() {
                        clippy.set_checked(false); // no web view on this computer
                    }
                } else if !on {
                    desk = None;
                }
                set_flag(desk.is_some());
            } else if ev.id == folder_id {
                show_folder(&db_path);
            } else if ev.id == quit_id {
                desk = None;
                tray.take(); // removes the icon at once
                if let Some(s) = stop.take() {
                    s();
                }
                *control_flow = ControlFlow::Exit;
            }
        }
        // A left click on the icon opens the library (the menu is on right click).
        while let Ok(ev) = TrayIconEvent::receiver().try_recv() {
            if let TrayIconEvent::Click { button: MouseButton::Left, button_state: MouseButtonState::Up, .. } = ev {
                let _ = webbrowser::open(&addr);
            }
        }
    })
}
