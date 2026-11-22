# Gotchas

Traps we have hit once. Read the one for the area you touch before you change it.

## G1. The blue flash on click (UI)

A mouse click or a tap must not leave a blue ring or flash on a button. The browser shows one for a
tap (`-webkit-tap-highlight-color`) and for an element that got focus by click or by script
(`:focus`). Both look like a bug.

- Keep focus rings for keyboard users only: style `:focus-visible`, and set
  `:focus:not(:focus-visible) { outline: none; }`.
- Set `-webkit-tap-highlight-color: transparent` for everything.
- Do not make controls selectable text (`user-select: none` on buttons, chips and cards). Leave
  titles and notes selectable.
- Check it: click every new button with the mouse, then tab to it with the keyboard. Only the second
  one should show a ring.

## G2. No status codes in front of people (UI)

A toast once said "200" beside "Preview updated." Most people don't know HTTP codes. Toasts show an
icon (tick, info, warning) and a plain sentence. The code stays on the element as `data-code` for
debugging. A toast must also be true: "Preview updated." only when the preview changed.

## G3. Changed CSS or JS doesn't show (UI)

Pages load `sml.css?v=N` and `sml.js?v=N`, and browsers keep the old copy. Raise `N` in
`app/templates/base.html` with every change to those files, or you and every visitor will see the
old styles.

## G4. The demo can't fetch other websites (demo)

The demo runs in the browser on GitHub Pages, and browsers block reading other sites (CORS). It
can't fetch real previews. It knows the sample links' images (`KNOWN` in `demo/demo-api.js`) and
simulates the rest. Say "Previews are simulated" wherever that matters, and never let a demo button
claim it fetched something it didn't.
