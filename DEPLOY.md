# Publish to Streamlit Community Cloud

Follow these steps to deploy **Arcade Pinball V3** as-is to [share.streamlit.io](https://share.streamlit.io).

---

## 1. Put the app on GitHub

In a terminal, open the app folder and run:

```bash
cd "C:\Users\RANEN\Documents\Data Science Course\Visual Studio Respo\VS CODE\2025\2026\Handshake v12\arcade-pinball-v3"

# Initialize git (if not already)
git init

# Add and commit
git add .
git commit -m "Arcade Pinball V3 - ready for Streamlit Cloud"

# Create repo on GitHub first: github.com → New repository (e.g. arcade-pinball-v3)
# Then link and push (replace with YOUR repo URL)
git branch -M main
git remote add origin https://github.com/YOUR_USERNAME/arcade-pinball-v3.git
git push -u origin main
```

If the folder is already a git repo and you have a remote, just:

```bash
git add .
git commit -m "Update for deploy"
git push
```

---

## 2. Deploy on Streamlit Cloud

1. Go to **[share.streamlit.io](https://share.streamlit.io)** and sign in with **GitHub**.
2. Click **"New app"**.
3. Choose:
   - **Repository**: `YOUR_USERNAME/arcade-pinball-v3` (or whatever you named it).
   - **Branch**: `main`.
   - **Main file path**: `app.py`.
4. Click **"Deploy"**.

Streamlit will install from `requirements.txt` and run `streamlit run app.py`. Your app will get a URL like `https://your-app-name.streamlit.app`.

---

## 3. After deploy

- **Database**: The app uses SQLite. On Streamlit Cloud the filesystem is ephemeral, so the DB resets when the app restarts. For persistent data you’d need a cloud DB (e.g. PostgreSQL) and secrets.
- **Secrets**: If you add `.streamlit/secrets.toml` later, add the same keys in the Cloud app: **App settings → Secrets** in the Streamlit Cloud dashboard.

That’s it. The app is ready to publish as-is.
