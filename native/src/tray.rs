//! The icon by the clock (the Windows notification area, the macOS menu bar). It says SaveMyLinks
//! is on, opens your library with a click, and switches it off from its menu, so there is no
//! terminal window to keep open. Linux keeps the terminal for now (a tray there needs GTK).
use std::time::{Duration, Instant};

use tao::event::{Event, StartCause};
use tao::event_loop::{ControlFlow, EventLoopBuilder};
use tray_icon::menu::{Menu, MenuEvent, MenuItem, PredefinedMenuItem};
use tray_icon::{Icon, MouseButton, MouseButtonState, TrayIconBuilder, TrayIconEvent};

const ICON_PNG: &[u8] = include_bytes!("../../app/static/art/icon-32.png");

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

/// Runs on the main thread until "Switch off" is chosen; `stop` shuts the server down first.
pub fn run(addr: String, db_path: String, stop: impl FnOnce() + 'static) -> ! {
    #[allow(unused_mut)]
    let mut event_loop = EventLoopBuilder::new().build();
    #[cfg(target_os = "macos")]
    {
        // A menu-bar app: no Dock icon.
        use tao::platform::macos::{ActivationPolicy, EventLoopExtMacOS};
        event_loop.set_activation_policy(ActivationPolicy::Accessory);
    }

    let menu = Menu::new();
    let status = MenuItem::new("SaveMyLinks is on", false, None);
    let open = MenuItem::new("Open your library", true, None);
    let folder = MenuItem::new("Show where your links are kept", true, None);
    let quit = MenuItem::new("Switch off SaveMyLinks", true, None);
    let _ = menu.append_items(&[
        &status,
        &PredefinedMenuItem::separator(),
        &open,
        &folder,
        &PredefinedMenuItem::separator(),
        &quit,
    ]);
    let (open_id, folder_id, quit_id) = (open.id().clone(), folder.id().clone(), quit.id().clone());
    let tooltip = format!("SaveMyLinks is on ({})\nClick to open your library", addr.trim_end_matches('/'));

    let mut tray = None;
    let mut stop = Some(stop);
    event_loop.run(move |event, _, control_flow| {
        *control_flow = ControlFlow::WaitUntil(Instant::now() + Duration::from_millis(200));

        // macOS needs the loop running before the icon is made.
        if let Event::NewEvents(StartCause::Init) = event {
            let mut b = TrayIconBuilder::new().with_menu(Box::new(menu.clone())).with_tooltip(&tooltip);
            if let Some(i) = icon() {
                b = b.with_icon(i);
            }
            tray = b.build().ok();
        }

        while let Ok(ev) = MenuEvent::receiver().try_recv() {
            if ev.id == open_id {
                let _ = webbrowser::open(&addr);
            } else if ev.id == folder_id {
                show_folder(&db_path);
            } else if ev.id == quit_id {
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
