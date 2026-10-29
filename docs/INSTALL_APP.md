# Use PRism Like an App

PRism is currently a Streamlit web app, not a native Android/iOS package. You can still launch it from your home screen or desktop so it behaves much more like a normal app.

**Live URL:** https://prism-prakhargoyal-0002.streamlit.app/

## Android — Chrome or Brave

1. Open the PRism live URL.
2. Open the browser menu (`⋮`).
3. Choose **Add to Home screen** or **Install app** if your browser offers it.
4. Confirm the name `PRism`.
5. Launch PRism from the new home-screen icon.

If the browser only offers **Create shortcut / Add to Home screen**, that is fine. PRism still opens directly from the icon.

## iPhone / iPad — Safari

1. Open PRism in Safari.
2. Tap **Share**.
3. Scroll to **Add to Home Screen**.
4. Name it `PRism`.
5. Tap **Add**.

## Windows — Chrome / Brave

1. Open PRism.
2. Open the browser menu.
3. Find **Save and share**, **More tools**, or the equivalent menu for your browser.
4. Choose **Create shortcut**.
5. Enable **Open as window** if that option is available.
6. Pin the shortcut to Start or the taskbar if you want one-click access.

## Windows — Microsoft Edge

1. Open PRism.
2. Open `…`.
3. Choose **Apps**.
4. Choose **Install this site as an app** if Edge offers it.
5. Pin the installed shortcut where you want it.

## Login behavior

PRism's private login is designed to survive normal refreshes and browser reopenings in the same browser profile by restoring the saved Supabase session.

You may need to sign in again if:

- you explicitly sign out;
- browser/site storage is cleared;
- you use incognito/private browsing;
- you switch to another browser profile/device;
- the saved Supabase session has expired or been revoked.

PRism does **not** store the account password in browser storage.

## Phone + desktop workflow

A practical setup:

```text
Desktop browser
    ↓
plan / import / review progress

Private Supabase state
    ↕
Phone home-screen shortcut
    ↓
Live Workout at the gym
```

Use the same private PRism account on trusted devices to open the same synced private state.
